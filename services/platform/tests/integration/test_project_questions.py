"""Grounded project questions through the restricted public database role."""

import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.engine import URL
from sqlalchemy.exc import DBAPIError

from shaidago.api.app import create_app
from shaidago.api.dependencies import Dependencies
from shaidago.retrieval.corpus import CorpusBuilder
from shaidago.retrieval.language import (
    PROMPT_VERSION,
    SCHEMA_VERSION,
    AnswerStatement,
    GroundedAnswer,
    GroundedAnswerRequest,
    LanguageModelError,
    LanguageModelResult,
    RetryClass,
)
from shaidago.shared.clock import ManualClock
from shaidago.shared.database import Database, build_engine
from shaidago.shared.ids import Uuid7Generator
from shaidago.shared.ratelimit import InMemoryRateLimiter
from tests.factories import CREDENTIAL, build_settings
from tests.integration.support import (
    DOCUMENT,
    Plain,
    insert_citation,
    insert_claim,
    insert_project,
    insert_source,
    insert_version,
)

NOW = datetime(2026, 9, 19, 19, 0, tzinfo=UTC)
AUTH = {"Authorization": f"Bearer web.{CREDENTIAL}"}
QUESTION = "When did the synthetic clinic open?"
ANSWER = "The synthetic clinic opened on 1 March."


class StubLanguageModel:
    model_id = "synthetic-question-model"

    def __init__(self) -> None:
        self.mode = "answer"
        self.requests: list[GroundedAnswerRequest] = []

    async def answer(self, request: GroundedAnswerRequest) -> LanguageModelResult:
        self.requests.append(request)
        if self.mode == "retryable":
            raise LanguageModelError("provider_timeout", RetryClass.RETRYABLE)
        if self.mode == "invalid":
            raise LanguageModelError("provider_invalid_schema", RetryClass.NON_RETRYABLE)
        statement = ANSWER if self.mode == "answer" else "Officials are corrupt."
        return LanguageModelResult(
            answer=GroundedAnswer(
                answer=statement,
                statements=(
                    AnswerStatement(
                        text=statement,
                        citation_ids=(request.passages[0].citation_id,),
                    ),
                ),
                insufficient_evidence=False,
                confidence_note="The supplied passage covers the opening date only.",
                generated_at=request.generated_at,
                locale=request.locale,
            ),
            model_id=self.model_id,
            prompt_version=PROMPT_VERSION,
            schema_version=SCHEMA_VERSION,
            demo_replay=True,
        )


@dataclass
class Harness:
    client: httpx.AsyncClient
    owner: Plain
    public: Database
    model: StubLanguageModel
    slug: str
    empty_slug: str

    async def metrics(self) -> list[tuple[object, ...]]:
        async with self.owner.unit_of_work() as session:
            rows = (
                await session.execute(
                    text(
                        "SELECT requested_locale, served_locale, retrieval_mode, "
                        "retrieved_chunks, cited_sources, outcome, model_id, prompt_version, "
                        "schema_version, demo_replay, failure_code, validation_findings "
                        "FROM app.question_runs r JOIN app.projects p ON p.id = r.project_id "
                        "WHERE p.slug = ANY(:slugs) ORDER BY r.started_at, r.id"
                    ),
                    {"slugs": [self.slug, self.empty_slug]},
                )
            ).all()
            return [tuple(row) for row in rows]


@pytest.fixture
async def questions(role_urls: dict[str, URL]) -> AsyncIterator[Harness]:
    owner_engine = build_engine(
        role_urls["owner"], application_name="question-owner", statement_timeout_ms=8000
    )
    worker_engine = build_engine(
        role_urls["shaidago_worker"],
        application_name="question-worker",
        statement_timeout_ms=8000,
    )
    public_engine = build_engine(
        role_urls["shaidago_public"],
        application_name="question-api",
        statement_timeout_ms=8000,
    )
    owner = Plain(owner_engine)
    worker = Database(worker_engine)
    public = Database(public_engine)
    slug = f"synthetic-question-{uuid.uuid4().hex[:8]}"
    empty_slug = f"synthetic-empty-{uuid.uuid4().hex[:8]}"
    async with owner.unit_of_work() as session:
        project = await insert_project(session, slug)
        await insert_project(session, empty_slug)
        source = await insert_source(session)
        version = await insert_version(session, source, content=DOCUMENT)
        claim = await insert_claim(
            session,
            "fact",
            project,
            visibility="public",
            state="verified_official",
            published=NOW,
        )
        await insert_citation(session, "fact", claim, version)
    clock = ManualClock(NOW)
    async with worker.unit_of_work() as session:
        await CorpusBuilder(session, clock=clock, ids=Uuid7Generator(clock)).refresh()
    model = StubLanguageModel()
    app = create_app(
        build_settings(RATE_QA_PER_HOUR="20"),
        Dependencies(
            public_database=public,
            language_model=model,
            rate_limiter=InMemoryRateLimiter(clock),
            clock=clock,
            ids=Uuid7Generator(clock),
            monotonic=iter((10.0, 10.125) * 20).__next__,
        ),
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test", headers=AUTH
    ) as client:
        yield Harness(client, owner, public, model, slug, empty_slug)
    for engine in (public_engine, worker_engine, owner_engine):
        await engine.dispose()


async def test_answer_is_grounded_linked_no_store_and_question_is_not_persisted(
    questions: Harness,
) -> None:
    response = await questions.client.post(
        f"/v1/projects/{questions.slug}/questions",
        json={"question": f"  {QUESTION}  "},
    )

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    assert body["answer"] == ANSWER
    assert body["insufficient_evidence"] is False
    assert body["retrieval"] == {"mode": "keyword", "chunks_considered": 1}
    assert body["statements"][0]["citation_ids"] == [body["sources"][0]["citation_id"]]
    assert body["sources"][0]["url"].startswith("https://synthetic.example/")
    assert questions.model.requests[0].question == QUESTION

    metrics = await questions.metrics()
    assert tuple(metrics[-1]) == (
        "en",
        "en",
        "keyword",
        1,
        1,
        "answered",
        "synthetic-question-model",
        PROMPT_VERSION,
        SCHEMA_VERSION,
        True,
        None,
        0,
    )
    async with questions.owner.unit_of_work() as session:
        columns = (
            await session.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema = 'app' AND table_name = 'question_runs'"
                )
            )
        ).scalars()
        assert not {"question", "prompt", "passage", "client_hmac"} & set(columns)


async def test_empty_corpus_and_unsafe_or_invalid_output_fail_closed(questions: Harness) -> None:
    empty = await questions.client.post(
        f"/v1/projects/{questions.empty_slug}/questions", json={"question": QUESTION}
    )
    assert empty.status_code == 200
    assert empty.json()["answer"] == "The available sources do not confirm this"
    assert empty.json()["sources"] == []
    assert len(questions.model.requests) == 0

    for mode in ("unsafe", "invalid"):
        questions.model.mode = mode
        response = await questions.client.post(
            f"/v1/projects/{questions.slug}/questions", json={"question": QUESTION}
        )
        assert response.status_code == 200
        assert response.json()["answer"] == "The available sources do not confirm this"
        assert response.json()["statements"] == []
        assert len(response.json()["sources"]) == 1
        assert "corrupt" not in response.text
    outcomes = [tuple(row)[5:] for row in await questions.metrics()]
    assert outcomes[0][0] == "fallback"
    assert outcomes[1][0] == "fallback"
    assert outcomes[2][0] == "fallback"
    assert outcomes[2][5] == "provider_invalid_schema"


async def test_retryable_provider_failure_is_a_safe_problem_and_is_recorded(
    questions: Harness,
) -> None:
    questions.model.mode = "retryable"
    response = await questions.client.post(
        f"/v1/projects/{questions.slug}/questions", json={"question": QUESTION}
    )

    assert response.status_code == 503
    assert response.headers["content-type"] == "application/problem+json"
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["code"] == "question_answering_unavailable"
    assert QUESTION not in response.text
    metric = tuple((await questions.metrics())[-1])
    assert metric[5] == "provider_unavailable"
    assert metric[10] == "provider_timeout"


async def test_project_resolution_validation_unknown_parameters_and_rate_limit(
    questions: Harness,
) -> None:
    missing = await questions.client.post(
        "/v1/projects/synthetic-does-not-exist/questions", json={"question": QUESTION}
    )
    assert missing.status_code == 404
    for body in ({}, {"question": ""}, {"question": "x" * 301}, {"question": "a\nb"}):
        response = await questions.client.post(
            f"/v1/projects/{questions.slug}/questions", json=body
        )
        assert response.status_code == 422
        assert response.json()["code"] == "validation_failed"
    unknown = await questions.client.post(
        f"/v1/projects/{questions.slug}/questions?extra=1", json={"question": QUESTION}
    )
    assert unknown.status_code == 422


async def test_public_role_can_append_metrics_but_cannot_read_them(questions: Harness) -> None:
    assert (
        await questions.client.post(
            f"/v1/projects/{questions.empty_slug}/questions", json={"question": QUESTION}
        )
    ).status_code == 200
    with pytest.raises(DBAPIError):
        async with questions.public.unit_of_work() as session:
            await session.execute(text("SELECT * FROM app.question_runs"))


async def test_questions_are_rate_limited_per_pseudonymous_client(questions: Harness) -> None:
    for _ in range(20):
        response = await questions.client.post(
            f"/v1/projects/{questions.empty_slug}/questions", json={"question": QUESTION}
        )
        assert response.status_code == 200
    blocked = await questions.client.post(
        f"/v1/projects/{questions.empty_slug}/questions", json={"question": QUESTION}
    )
    assert blocked.status_code == 429
    assert blocked.json()["code"] == "rate_limited"
    assert blocked.headers["cache-control"] == "no-store"
