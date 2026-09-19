"""Hybrid retrieval stays inside the selected approved public project."""

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.engine import URL

from shaidago.retrieval.corpus import CorpusBuilder
from shaidago.retrieval.embeddings import EMBEDDINGS_ROOT, load_embeddings
from shaidago.retrieval.search import EMBEDDING_DIMENSIONS, Retriever
from shaidago.shared.clock import ManualClock
from shaidago.shared.database import Database, build_engine
from shaidago.shared.ids import SequentialIds
from tests.integration.support import (
    DOCUMENT,
    Plain,
    insert_citation,
    insert_claim,
    insert_project,
    insert_source,
    insert_version,
)

NOW = datetime(2026, 9, 19, 16, 0, tzinfo=UTC)
MODEL = "fixture-hash-v1"


@pytest.fixture
async def owner(role_urls: dict[str, URL]) -> AsyncIterator[Plain]:
    engine = build_engine(
        role_urls["owner"], application_name="retrieval-owner", statement_timeout_ms=8000
    )
    yield Plain(engine)
    await engine.dispose()


@pytest.fixture
async def worker(role_urls: dict[str, URL]) -> AsyncIterator[Database]:
    engine = build_engine(
        role_urls["shaidago_worker"],
        application_name="retrieval-worker",
        statement_timeout_ms=8000,
    )
    yield Database(engine)
    await engine.dispose()


@pytest.fixture
async def public(role_urls: dict[str, URL]) -> AsyncIterator[Database]:
    engine = build_engine(
        role_urls["shaidago_public"],
        application_name="retrieval-public",
        statement_timeout_ms=8000,
    )
    yield Database(engine)
    await engine.dispose()


async def approved_document(
    owner: Plain, *, second_source: bool = False
) -> tuple[uuid.UUID, uuid.UUID]:
    async with owner.unit_of_work() as session:
        project = await insert_project(session)
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
        if second_source:
            other_source = await insert_source(session)
            other_version = await insert_version(session, other_source, content=DOCUMENT)
            await insert_citation(
                session,
                "fact",
                claim,
                other_version,
                label="section 2",
            )
    return project, source


async def refresh(worker: Database, *, first_id: int) -> None:
    async with worker.unit_of_work() as session:
        await CorpusBuilder(
            session,
            clock=ManualClock(NOW),
            ids=SequentialIds(start=first_id),
        ).refresh()


async def search(
    public: Database,
    project: uuid.UUID,
    *,
    query_embedding: list[float] | None = None,
    model: str | None = None,
):
    async with public.unit_of_work() as session:
        return await Retriever(session).search(
            project,
            "synthetic clinic",
            query_embedding=query_embedding,
            embedding_model=model,
            limit=10,
        )


async def test_keyword_search_is_project_scoped_and_empty_corpora_stay_empty(
    owner: Plain, worker: Database, public: Database
) -> None:
    selected, _source = await approved_document(owner)
    other, _other_source = await approved_document(owner)
    async with owner.unit_of_work() as session:
        empty = await insert_project(session)
    await refresh(worker, first_id=10_000)

    result = await search(public, selected)
    assert result.mode == "keyword"
    assert result.chunks
    assert {chunk.project_id for chunk in result.chunks} == {selected}
    assert other not in {chunk.project_id for chunk in result.chunks}

    empty_result = await search(public, empty)
    assert empty_result.mode == "keyword"
    assert empty_result.chunks == ()


async def test_public_view_excludes_a_source_immediately_when_it_becomes_unavailable(
    owner: Plain, worker: Database, public: Database
) -> None:
    project, source = await approved_document(owner)
    await refresh(worker, first_id=20_000)
    assert (await search(public, project)).chunks

    async with owner.unit_of_work() as session:
        await session.execute(
            text("UPDATE app.sources SET availability = 'temporarily_unavailable' WHERE id = :id"),
            {"id": source},
        )

    assert (await search(public, project)).chunks == ()


async def test_rank_ties_are_deterministic_and_model_mismatch_falls_back_to_keyword(
    owner: Plain, worker: Database, public: Database
) -> None:
    project, _source = await approved_document(owner, second_source=True)
    await refresh(worker, first_id=30_000)
    vector = [1.0, *([0.0] * (EMBEDDING_DIMENSIONS - 1))]

    first = await search(public, project, query_embedding=vector, model="missing-model")
    second = await search(public, project, query_embedding=vector, model="missing-model")

    assert first.mode == "keyword"
    assert len(first.chunks) == 2
    assert [chunk.id for chunk in first.chunks] == [chunk.id for chunk in second.chunks]


async def test_checked_fixture_enables_hybrid_mode_and_reports_unmatched_records(
    owner: Plain, worker: Database, public: Database
) -> None:
    project, _source = await approved_document(owner)
    await refresh(worker, first_id=40_000)
    fixture = EMBEDDINGS_ROOT / f"{MODEL}.jsonl"

    async with worker.unit_of_work() as session:
        loaded = await load_embeddings(session, fixture, expected_model=MODEL, now=NOW)

    vector = [1.0, *([0.0] * (EMBEDDING_DIMENSIONS - 1))]
    result = await search(public, project, query_embedding=vector, model=MODEL)
    assert loaded.records == 1
    assert loaded.matched_chunks >= 1
    assert loaded.unmatched_records == 0
    assert result.mode == "hybrid"
    assert result.chunks
