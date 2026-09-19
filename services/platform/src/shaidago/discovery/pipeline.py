"""The Source Scout stages a worker runs for one discovery run.

``search`` runs the approved query, fetches at most ten public pages through the safe fetcher,
extracts inert text, and records each page as ``not_reviewed``. ``analyse`` gives the model only
the recorded excerpts (never a page flagged as an injection attempt) under opaque IDs, validates
the result, and stores it. Both stages are safe to run again for the same run: recording
deduplicates and analysis overwrites. Cancellation is honoured between pages.
"""

import hashlib
from collections.abc import Callable
from typing import Any, Final
from uuid import UUID

from sqlalchemy import text

from shaidago.discovery.analysis import (
    LABEL,
    AnalysisProvider,
    SourcePassage,
    analyse_sources,
)
from shaidago.discovery.extract import ExtractionError, extract
from shaidago.discovery.fetcher import FetchError
from shaidago.discovery.netguard import UnsafeDestinationError
from shaidago.discovery.pages import PageFetcher
from shaidago.discovery.planner import UnsafeQueryError
from shaidago.discovery.records import Scope, SourceRecorder
from shaidago.discovery.search import (
    SearchProvider,
    SearchRejectedError,
    SearchUnavailableError,
)
from shaidago.retrieval.language import LanguageModelError, RetryClass
from shaidago.worker.process import AnalysisResult, PermanentStageError, TransientStageError
from shaidago.worker.store import RunStore, RunView

MAX_ANALYSED_SOURCES: Final = 8
_SIGHTED = text(
    "SELECT d.id, d.canonical_url, d.text_sha256, d.publisher_domain, d.excerpt "
    "FROM app.discovered_source_sightings s "
    "JOIN app.discovered_sources d ON d.id = s.discovered_source_id "
    "WHERE s.run_id = :run AND d.duplicate_of IS NULL AND NOT d.injection_flag "
    "ORDER BY d.first_discovered_at, d.id LIMIT :limit"
)


def citation_id(canonical_url: str, text_sha256: str) -> str:
    """An opaque label derived from the page's own URL and content, so the same page always gets
    the same label (replay fixtures stay valid) and nothing in it names a run or a person."""
    return "s_" + hashlib.sha256(f"{canonical_url}\n{text_sha256}".encode()).hexdigest()[:12]


class SourceScoutPipeline:
    def __init__(
        self,
        search: SearchProvider,
        fetcher: PageFetcher,
        analyser_for: Callable[[str], AnalysisProvider],
    ) -> None:
        self._search = search
        self._fetcher = fetcher
        self._analyser_for = analyser_for

    async def search(self, run: RunView, store: RunStore) -> None:
        if not run.query_text:
            raise PermanentStageError("query_not_approved")
        try:
            results = await self._search.search(run.query_text)
        except SearchUnavailableError:
            raise TransientStageError from None
        except SearchRejectedError:
            raise PermanentStageError("search_rejected") from None
        except UnsafeQueryError:
            raise PermanentStageError("unsafe_query") from None
        found = len(results.urls)
        await store.progress(run.id, found=found, fetched=0, analysed=0)
        scope = Scope("report" if run.report_id else "public", run.project_id, run.report_id)
        fetched = 0
        for url in results.urls:
            latest = await store.load(run.id)
            if latest is None or latest.cancel_requested:
                return  # the run loop turns the request into a cancellation
            try:
                page = await self._fetcher.fetch(url)
                extracted = extract(page.content_type, page.body, page.final_url)
            except FetchError, UnsafeDestinationError, ExtractionError:
                continue  # an unreachable, blocked, or unreadable page is skipped, not fatal
            async with store.database.unit_of_work() as session:
                await SourceRecorder(session, store.ids).record(
                    scope, run.id, extracted, store.now()
                )
            fetched += 1
            await store.progress(run.id, found=found, fetched=fetched, analysed=0)

    async def analyse(self, run: RunView, store: RunStore) -> AnalysisResult:
        async with store.database.unit_of_work() as session:
            rows = (
                await session.execute(_SIGHTED, {"run": run.id, "limit": MAX_ANALYSED_SOURCES})
            ).all()
        if not rows:
            await self._save(
                store,
                run.id,
                _envelope("no_sources", None, None, "none", "none", True),
                "none",
                "none",
            )
            return AnalysisResult(needs_review=False)
        passages = tuple(
            SourcePassage(
                citation_id=citation_id(r.canonical_url, r.text_sha256),
                publisher_domain=r.publisher_domain,
                text=r.excerpt,
            )
            for r in rows
        )
        try:
            outcome = await analyse_sources(self._analyser_for(run.scope), passages, store.now())
        except LanguageModelError as error:
            if error.code == "provider_fixture_missing":
                await self._save(
                    store,
                    run.id,
                    _envelope("needs_review", None, "replay_unavailable", "fixture", "none", True),
                    "fixture",
                    "none",
                )
                return AnalysisResult(needs_review=True)
            if error.retry_class is RetryClass.RETRYABLE:
                raise TransientStageError from None
            raise PermanentStageError("analysis_provider_error") from None
        body: dict[str, Any] | None = (
            None if outcome.analysis is None else outcome.analysis.model_dump(mode="json")
        )
        payload = _envelope(
            outcome.status,
            body,
            outcome.failure_code,
            outcome.model_id,
            outcome.prompt_version,
            outcome.demo_replay,
        )
        payload["sources"] = [
            {"citation_id": p.citation_id, "source_id": str(r.id)}
            for p, r in zip(passages, rows, strict=True)
        ]
        await self._save(store, run.id, payload, outcome.model_id, outcome.prompt_version)
        await store.progress(
            run.id, found=run.results_found, fetched=run.fetched_count, analysed=len(passages)
        )
        return AnalysisResult(needs_review=outcome.status == "needs_review")

    @staticmethod
    async def _save(
        store: RunStore, run_id: UUID, payload: dict[str, object], model: str, prompt: str
    ) -> None:
        await store.save_analysis(run_id, payload, model_id=model, prompt_version=prompt)


def _envelope(  # noqa: PLR0913, PLR0917 - a stored envelope names each of its fields
    status: str,
    analysis: dict[str, Any] | None,
    failure_code: str | None,
    model_id: str,
    prompt_version: str,
    demo_replay: bool,
) -> dict[str, object]:
    return {
        "label": LABEL,
        "status": status,
        "analysis": analysis,
        "failure_code": failure_code,
        "model_id": model_id,
        "prompt_version": prompt_version,
        "demo_replay": demo_replay,
    }
