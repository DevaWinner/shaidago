"""The grounded-Q&A corpus contains approved public evidence only.

All records are synthetic. The tests exercise the worker and public database roles rather than
the migration owner wherever the production path does.
"""

import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import UTC, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.engine import URL
from sqlalchemy.exc import DBAPIError

from shaidago.retrieval.corpus import CorpusBuilder, CorpusRefresh
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

NOW = datetime(2026, 9, 19, 15, 0, tzinfo=UTC)
CONTENT = DOCUMENT
PRIVILEGE = "42501"
CHECK_VIOLATION = "23514"
IMMUTABLE = "55000"


@pytest.fixture
async def owner(role_urls: dict[str, URL]) -> AsyncIterator[Plain]:
    engine = build_engine(
        role_urls["owner"], application_name="chunk-owner", statement_timeout_ms=8000
    )
    yield Plain(engine)
    await engine.dispose()


@pytest.fixture
async def worker(role_urls: dict[str, URL]) -> AsyncIterator[Database]:
    engine = build_engine(
        role_urls["shaidago_worker"], application_name="chunk-worker", statement_timeout_ms=8000
    )
    yield Database(engine)
    await engine.dispose()


@pytest.fixture
async def public(role_urls: dict[str, URL]) -> AsyncIterator[Plain]:
    engine = build_engine(
        role_urls["shaidago_public"], application_name="chunk-public", statement_timeout_ms=8000
    )
    yield Plain(engine)
    await engine.dispose()


async def sqlstate_of(action: Callable[[], Awaitable[object]]) -> str | None:
    with pytest.raises(DBAPIError) as raised:
        await action()
    return getattr(raised.value.orig, "sqlstate", None)


async def public_document(
    owner: Plain, *, content: str = CONTENT, second_source: bool = False
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID | None]:
    async with owner.unit_of_work() as session:
        project = await insert_project(session)
        source = await insert_source(session)
        version = await insert_version(session, source, content=content)
        claim = await insert_claim(
            session,
            "fact",
            project,
            visibility="public",
            state="verified_official",
            published=NOW,
        )
        await insert_citation(
            session,
            "fact",
            claim,
            version,
            passage="The synthetic clinic opened on 1 March.",
        )
        other_version = None
        if second_source:
            other_source = await insert_source(session)
            other_version = await insert_version(session, other_source, content=content)
            await insert_citation(
                session,
                "fact",
                claim,
                other_version,
                passage="The synthetic clinic opened on 1 March.",
                label="section 2",
            )
    return project, source, version, other_version


async def refresh(worker: Database, *, first_id: int = 1) -> CorpusRefresh:
    async with worker.unit_of_work() as session:
        return await CorpusBuilder(
            session,
            clock=ManualClock(NOW),
            ids=SequentialIds(start=first_id),
        ).refresh()


async def test_worker_builds_exact_deterministic_chunks_with_public_citation_metadata(
    owner: Plain, worker: Database, public: Plain
) -> None:
    project, source, version, _other = await public_document(owner)

    first = await refresh(worker)
    async with public.unit_of_work() as session:
        row = (
            await session.execute(
                text(
                    "SELECT * FROM public_api.source_chunks "
                    "WHERE project_id = :project AND source_version_id = :version"
                ),
                {"project": project, "version": version},
            )
        ).one()
    assert first == CorpusRefresh(1, 1, 0, 0, 0)
    assert row.source_id == source
    assert row.content_text == CONTENT[row.passage_start : row.passage_end]
    assert row.language == "en"
    assert row.section_label is None
    assert row.source_title == "Synthetic source"
    assert row.publisher == "Synthetic Publisher"
    assert str(row.canonical_url).startswith("https://synthetic.example/")

    second = await refresh(worker, first_id=50)
    async with public.unit_of_work() as session:
        repeated = (
            await session.execute(
                text(
                    "SELECT id, text_sha256, passage_start, passage_end "
                    "FROM public_api.source_chunks WHERE project_id = :project"
                ),
                {"project": project},
            )
        ).one()
    assert second == CorpusRefresh(1, 0, 0, 1, 0)
    assert repeated.id == row.id
    assert repeated.text_sha256 == row.text_sha256
    assert (repeated.passage_start, repeated.passage_end) == (
        row.passage_start,
        row.passage_end,
    )


async def test_refresh_deactivates_unavailable_or_unapproved_sources_and_can_reactivate(
    owner: Plain, worker: Database, public: Plain
) -> None:
    project, source, version, other_version = await public_document(owner, second_source=True)
    assert other_version is not None
    await refresh(worker, first_id=1_000)
    async with owner.unit_of_work() as session:
        chunk_id = (
            await session.execute(
                text(
                    "SELECT id FROM app.source_chunks "
                    "WHERE project_id = :project AND source_version_id = :version"
                ),
                {"project": project, "version": version},
            )
        ).scalar_one()
        await session.execute(
            text("UPDATE app.sources SET availability = 'temporarily_unavailable' WHERE id = :id"),
            {"id": source},
        )

    unavailable = await refresh(worker, first_id=100)
    assert unavailable.deactivated == 1
    async with public.unit_of_work() as session:
        assert (
            await session.scalar(
                text("SELECT count(*) FROM public_api.source_chunks WHERE source_id = :source"),
                {"source": source},
            )
            == 0
        )

    async with owner.unit_of_work() as session:
        await session.execute(
            text("UPDATE app.sources SET availability = 'available' WHERE id = :id"),
            {"id": source},
        )
    available = await refresh(worker, first_id=200)
    assert available.reactivated_or_changed == 1
    async with owner.unit_of_work() as session:
        assert (
            await session.scalar(
                text("SELECT id FROM app.source_chunks WHERE source_version_id = :version"),
                {"version": version},
            )
            == chunk_id
        )
        await session.execute(
            text(
                "UPDATE app.source_versions SET review_state = 'in_review', reviewed_at = :now "
                "WHERE id = :version"
            ),
            {"version": version, "now": NOW},
        )
    unapproved = await refresh(worker, first_id=300)
    assert unapproved.deactivated == 1


async def test_drafts_pending_versions_and_unavailable_sources_never_enter_the_corpus(
    owner: Plain, worker: Database
) -> None:
    async with owner.unit_of_work() as session:
        project = await insert_project(session)
        source = await insert_source(session)
        approved = await insert_version(session, source, content=CONTENT)
        draft = await insert_claim(session, "fact", project)
        await insert_citation(session, "fact", draft, approved)

        pending_source = await insert_source(session)
        pending = await insert_version(session, pending_source, content=CONTENT, state="pending")
        pending_claim = await insert_claim(session, "fact", project)
        await insert_citation(session, "fact", pending_claim, pending)

    await refresh(worker, first_id=2_000)
    async with owner.unit_of_work() as session:
        assert (
            await session.scalar(
                text("SELECT count(*) FROM app.source_chunks WHERE project_id = :project"),
                {"project": project},
            )
            == 0
        )


async def test_database_rejects_forged_chunks_and_role_boundary_bypasses(
    owner: Plain, worker: Database, public: Plain
) -> None:
    project, _source, version, _other = await public_document(owner)
    await refresh(worker, first_id=3_000)

    async def public_reads_table() -> None:
        async with public.unit_of_work() as session:
            await session.execute(text("SELECT * FROM app.source_chunks"))

    async def worker_deletes_chunk() -> None:
        async with worker.unit_of_work() as session:
            await session.execute(text("DELETE FROM app.source_chunks"))

    async def owner_forges_text() -> None:
        async with owner.unit_of_work() as session:
            await session.execute(
                text(
                    "UPDATE app.source_chunks SET content_text = 'private report canary' "
                    "WHERE project_id = :project AND source_version_id = :version"
                ),
                {"project": project, "version": version},
            )

    async def owner_relabels_language() -> None:
        async with owner.unit_of_work() as session:
            await session.execute(
                text("UPDATE app.source_versions SET language = 'ha' WHERE id = :version"),
                {"version": version},
            )

    assert await sqlstate_of(public_reads_table) == PRIVILEGE
    assert await sqlstate_of(worker_deletes_chunk) == PRIVILEGE
    assert await sqlstate_of(owner_forges_text) == CHECK_VIOLATION
    assert await sqlstate_of(owner_relabels_language) == IMMUTABLE
