"""One grounded project-question use case with privacy-safe operational persistence."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from time import monotonic
from typing import Literal
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shaidago.projects.models import Locale
from shaidago.projects.repository import PublicProjectRepository
from shaidago.retrieval.language import (
    PROMPT_VERSION,
    SCHEMA_VERSION,
    EvidencePassage,
    GroundedAnswer,
    GroundedAnswerRequest,
    LanguageModel,
    LanguageModelError,
    RetryClass,
)
from shaidago.retrieval.search import RetrievalMode, RetrievedChunk, Retriever, normalise_query
from shaidago.retrieval.validation import CitationEvidence, ValidationDecision, validate_answer
from shaidago.shared.clock import Clock
from shaidago.shared.database import Database
from shaidago.shared.ids import IdGenerator

MAX_QUESTION_SOURCES = 5
MAX_DURATION_MS = 120_000
QuestionOutcome = Literal["answered", "fallback", "provider_unavailable"]

_INSERT_METRIC = text(
    "INSERT INTO app.question_runs "
    "(id, project_id, request_id, requested_locale, served_locale, retrieval_mode, "
    "retrieved_chunks, cited_sources, outcome, model_id, prompt_version, schema_version, "
    "demo_replay, failure_code, validation_findings, duration_ms, started_at, completed_at) "
    "VALUES (:id, :project, :request, :requested_locale, :served_locale, :retrieval_mode, "
    ":retrieved_chunks, :cited_sources, :outcome, :model, :prompt, :schema, :demo_replay, "
    ":failure_code, :validation_findings, :duration_ms, :started_at, :completed_at)"
)


class ProjectQuestionNotFoundError(Exception):
    """The slug does not resolve through the public project boundary."""


class QuestionProviderUnavailableError(Exception):
    """The language provider failed in a way a later request may safely retry."""


@dataclass(frozen=True)
class QuestionSource:
    citation_id: str
    source_id: UUID
    title: str
    publisher: str
    url: str
    retrieved_at: datetime
    passage: str
    section_label: str | None


@dataclass(frozen=True)
class QuestionResult:
    decision: ValidationDecision
    retrieval_mode: RetrievalMode
    retrieved_chunks: int
    sources: tuple[QuestionSource, ...]


@dataclass(frozen=True)
class QuestionMetric:
    id: UUID
    project_id: UUID
    request_id: str
    requested_locale: Locale
    served_locale: Locale | None
    retrieval_mode: RetrievalMode
    retrieved_chunks: int
    cited_sources: int
    outcome: QuestionOutcome
    model_id: str
    prompt_version: str
    schema_version: str
    demo_replay: bool | None
    failure_code: str | None
    validation_findings: int
    duration_ms: int
    started_at: datetime
    completed_at: datetime


@dataclass(frozen=True)
class MetricContext:
    project_id: UUID
    request_id: str
    locale: Locale
    retrieval_mode: RetrievalMode
    retrieved_chunks: int
    started_at: datetime
    timer: float


@dataclass(frozen=True)
class MetricCompletion:
    served_locale: Locale | None
    cited_sources: int
    outcome: QuestionOutcome
    demo_replay: bool | None
    failure_code: str | None
    validation_findings: int
    model_id: str
    prompt_version: str
    schema_version: str


def _citation_id(chunk: RetrievedChunk) -> str:
    return f"c_{chunk.id.hex}"


def _evidence(chunks: tuple[RetrievedChunk, ...]) -> tuple[CitationEvidence, ...]:
    return tuple(
        CitationEvidence(
            citation_id=_citation_id(chunk),
            project_id=chunk.project_id,
            passage=chunk.text,
            source_title=chunk.source_title,
            source_url=chunk.canonical_url,
            available=True,
        )
        for chunk in chunks
    )


def _fallback_answer(generated_at: datetime, locale: Locale) -> GroundedAnswer:
    return GroundedAnswer(
        answer="",
        statements=(),
        insufficient_evidence=True,
        confidence_note="Insufficient approved source coverage.",
        generated_at=generated_at,
        locale=locale,
    )


def _sources(
    chunks: tuple[RetrievedChunk, ...], decision: ValidationDecision
) -> tuple[QuestionSource, ...]:
    by_citation = {_citation_id(chunk): chunk for chunk in chunks}
    selected: list[RetrievedChunk] = []
    if decision.used_provider_answer:
        identifiers = (
            citation_id
            for statement in decision.answer.statements
            for citation_id in statement.citation_ids
        )
        selected = [by_citation[value] for value in dict.fromkeys(identifiers)]
    else:
        allowed = {(link.title, link.url) for link in decision.source_links}
        seen: set[tuple[str, str]] = set()
        for chunk in chunks:
            key = (chunk.source_title, chunk.canonical_url)
            if key in allowed and key not in seen:
                selected.append(chunk)
                seen.add(key)
    return tuple(
        QuestionSource(
            citation_id=_citation_id(chunk),
            source_id=chunk.source_id,
            title=chunk.source_title,
            publisher=chunk.publisher,
            url=chunk.canonical_url,
            retrieved_at=chunk.retrieved_at,
            passage=chunk.text,
            section_label=chunk.section_label,
        )
        for chunk in selected[:MAX_QUESTION_SOURCES]
    )


async def _record(session: AsyncSession, metric: QuestionMetric) -> None:
    await session.execute(
        _INSERT_METRIC,
        {
            "id": metric.id,
            "project": metric.project_id,
            "request": metric.request_id,
            "requested_locale": metric.requested_locale,
            "served_locale": metric.served_locale,
            "retrieval_mode": metric.retrieval_mode,
            "retrieved_chunks": metric.retrieved_chunks,
            "cited_sources": metric.cited_sources,
            "outcome": metric.outcome,
            "model": metric.model_id,
            "prompt": metric.prompt_version,
            "schema": metric.schema_version,
            "demo_replay": metric.demo_replay,
            "failure_code": metric.failure_code,
            "validation_findings": metric.validation_findings,
            "duration_ms": metric.duration_ms,
            "started_at": metric.started_at,
            "completed_at": metric.completed_at,
        },
    )


class ProjectQuestionService:
    def __init__(
        self,
        database: Database,
        model: LanguageModel,
        clock: Clock,
        ids: IdGenerator,
        *,
        elapsed: Callable[[], float] = monotonic,
    ) -> None:
        self._database = database
        self._model = model
        self._clock = clock
        self._ids = ids
        self._elapsed = elapsed

    async def ask(
        self,
        *,
        project_slug: str,
        question: str,
        locale: Locale,
        request_id: str,
    ) -> QuestionResult:
        """Answer from approved chunks and retain only bounded, content-free metrics."""
        safe_question = normalise_query(question)
        started_at = self._clock.now()
        timer = self._elapsed()
        async with self._database.unit_of_work() as session:
            projects = PublicProjectRepository(session)
            project = await projects.get_project(project_slug, locale)
            project_id = await projects.resolve_project_id(project_slug)
            if project is None or project_id is None:
                raise ProjectQuestionNotFoundError
            retrieval = await Retriever(session).search(
                project_id, safe_question, limit=MAX_QUESTION_SOURCES
            )

        evidence = _evidence(retrieval.chunks)
        metric_context = MetricContext(
            project_id=project_id,
            request_id=request_id,
            locale=locale,
            retrieval_mode=retrieval.mode,
            retrieved_chunks=len(retrieval.chunks),
            started_at=started_at,
            timer=timer,
        )
        failure_code: str | None = None
        demo_replay: bool | None = None
        model_id = self._model.model_id
        prompt_version = PROMPT_VERSION
        schema_version = SCHEMA_VERSION
        if not retrieval.chunks:
            answer = _fallback_answer(started_at, locale)
            decision = validate_answer(
                answer, expected_locale=locale, project_id=project_id, evidence=evidence
            )
        else:
            provider_request = GroundedAnswerRequest(
                locale=locale,
                question=safe_question,
                passages=tuple(
                    EvidencePassage(citation_id=item.citation_id, text=item.passage)
                    for item in evidence
                ),
                generated_at=started_at,
            )
            try:
                generated = await self._model.answer(provider_request)
            except LanguageModelError as error:
                failure_code = error.code
                if error.retry_class is RetryClass.RETRYABLE:
                    await self._persist_metric(
                        metric_context,
                        MetricCompletion(
                            served_locale=None,
                            cited_sources=0,
                            outcome="provider_unavailable",
                            demo_replay=None,
                            failure_code=error.code,
                            validation_findings=0,
                            model_id=model_id,
                            prompt_version=prompt_version,
                            schema_version=schema_version,
                        ),
                    )
                    raise QuestionProviderUnavailableError from None
                answer = _fallback_answer(started_at, locale)
            else:
                answer = generated.answer
                demo_replay = generated.demo_replay
                model_id = generated.model_id
                prompt_version = generated.prompt_version
                schema_version = generated.schema_version
            decision = validate_answer(
                answer, expected_locale=locale, project_id=project_id, evidence=evidence
            )

        sources = _sources(retrieval.chunks, decision)
        outcome: QuestionOutcome = "answered" if decision.used_provider_answer else "fallback"
        await self._persist_metric(
            metric_context,
            MetricCompletion(
                served_locale=decision.served_locale,
                cited_sources=len(sources),
                outcome=outcome,
                demo_replay=demo_replay,
                failure_code=failure_code,
                validation_findings=len(decision.findings),
                model_id=model_id,
                prompt_version=prompt_version,
                schema_version=schema_version,
            ),
        )
        return QuestionResult(
            decision=decision,
            retrieval_mode=retrieval.mode,
            retrieved_chunks=len(retrieval.chunks),
            sources=sources,
        )

    async def _persist_metric(
        self,
        context: MetricContext,
        completion: MetricCompletion,
    ) -> None:
        completed_at = self._clock.now()
        duration_ms = min(MAX_DURATION_MS, max(0, round((self._elapsed() - context.timer) * 1000)))
        metric = QuestionMetric(
            id=self._ids.new(),
            project_id=context.project_id,
            request_id=context.request_id,
            requested_locale=context.locale,
            served_locale=completion.served_locale,
            retrieval_mode=context.retrieval_mode,
            retrieved_chunks=context.retrieved_chunks,
            cited_sources=completion.cited_sources,
            outcome=completion.outcome,
            model_id=completion.model_id,
            prompt_version=completion.prompt_version,
            schema_version=completion.schema_version,
            demo_replay=completion.demo_replay,
            failure_code=completion.failure_code,
            validation_findings=completion.validation_findings,
            duration_ms=duration_ms,
            started_at=context.started_at,
            completed_at=completed_at,
        )
        async with self._database.unit_of_work() as session:
            await _record(session, metric)
