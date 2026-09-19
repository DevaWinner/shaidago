"""Immutable source versions, exact citations, fail-closed publication, and public views.

Every row is synthetic. Each test creates uniquely named data, so the module-scoped database is
shared without cleanup (source versions cannot be deleted, by design).
"""

import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import UTC, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.engine import URL
from sqlalchemy.exc import DBAPIError

from shaidago.shared.clock import ManualClock
from shaidago.shared.database import Database, build_engine
from shaidago.shared.problems import NOT_FOUND, PUBLICATION_INCOMPLETE, ProblemError
from shaidago.sources.publication import PublicationService
from tests.integration.support import (
    DOCUMENT,
    Plain,
    insert_citation,
    insert_claim,
    insert_project,
    insert_source,
    insert_version,
    sha256_hex,
)

CHECK_VIOLATION = "23514"
UNIQUE_VIOLATION = "23505"
IMMUTABLE = "55000"
PRIVILEGE = "42501"
START = datetime(2026, 9, 20, 9, 0, tzinfo=UTC)
LATER_DOCUMENT = DOCUMENT + " A later paragraph."


@pytest.fixture
async def owner(role_urls: dict[str, URL]) -> AsyncIterator[Plain]:
    engine = build_engine(role_urls["owner"], application_name="owner", statement_timeout_ms=8000)
    yield Plain(engine)
    await engine.dispose()


@pytest.fixture
async def public(role_urls: dict[str, URL]) -> AsyncIterator[Database]:
    engine = build_engine(
        role_urls["shaidago_public"], application_name="public", statement_timeout_ms=8000
    )
    yield Database(engine)
    await engine.dispose()


async def sqlstate_of(action: Callable[[], Awaitable[object]]) -> str | None:
    with pytest.raises(DBAPIError) as raised:
        await action()
    return getattr(raised.value.orig, "sqlstate", None)


async def approved_version(owner: Plain, **source: str) -> tuple[uuid.UUID, uuid.UUID]:
    async with owner.unit_of_work() as session:
        source_id = await insert_source(session, **source)
        return source_id, await insert_version(session, source_id)


# ---- immutable, content-addressed versions -------------------------------------------------


async def test_a_version_must_be_addressed_by_the_hash_of_its_text(owner: Plain) -> None:
    async with owner.unit_of_work() as session:
        source_id = await insert_source(session)

    async def wrong_hash() -> None:
        async with owner.unit_of_work() as session:
            await session.execute(
                text(
                    "INSERT INTO app.source_versions VALUES (gen_random_uuid(), :s, :sha, 'text', "
                    "'text/plain', now(), 'pending', NULL, NULL, now())"
                ),
                {"s": source_id, "sha": sha256_hex("different text")},
            )

    assert await sqlstate_of(wrong_hash) == CHECK_VIOLATION


async def test_the_same_content_is_one_version_and_changed_content_is_a_new_one(
    owner: Plain,
) -> None:
    async with owner.unit_of_work() as session:
        source_id = await insert_source(session)
        first = await insert_version(session, source_id, state="pending")

    async def duplicate() -> None:
        async with owner.unit_of_work() as session:
            await insert_version(session, source_id, state="pending")

    assert await sqlstate_of(duplicate) == UNIQUE_VIOLATION
    async with owner.unit_of_work() as session:
        second = await insert_version(session, source_id, content=LATER_DOCUMENT, state="pending")
    assert first != second


async def test_version_content_can_never_change_or_be_deleted(owner: Plain) -> None:
    _source, version = await approved_version(owner)

    async def edit(column: str, value: str) -> None:
        async with owner.unit_of_work() as session:
            await session.execute(
                text(f"UPDATE app.source_versions SET {column} = :v WHERE id = :id"),
                {"v": value, "id": version},
            )

    async def delete() -> None:
        async with owner.unit_of_work() as session:
            await session.execute(
                text("DELETE FROM app.source_versions WHERE id = :id"), {"id": version}
            )

    for column, value in (("content_text", "rewritten"), ("media_type", "text/html")):
        assert await sqlstate_of(lambda c=column, v=value: edit(c, v)) == IMMUTABLE
    assert await sqlstate_of(delete) == IMMUTABLE


@pytest.mark.parametrize(
    ("start", "end", "allowed"),
    [
        ("pending", "in_review", True),
        ("in_review", "approved", True),
        ("in_review", "rejected", True),
        ("approved", "superseded", True),
        ("approved", "in_review", True),
        ("rejected", "in_review", True),
        ("superseded", "in_review", True),
        ("pending", "approved", False),
        ("pending", "rejected", False),
        ("approved", "pending", False),
        ("approved", "rejected", False),
        ("rejected", "approved", False),
        ("superseded", "approved", False),
    ],
)
async def test_review_state_follows_the_controlled_state_machine(
    owner: Plain, start: str, end: str, allowed: bool
) -> None:
    async with owner.unit_of_work() as session:
        source_id = await insert_source(session)
        version = await insert_version(session, source_id, state=start)

    async def move() -> None:
        async with owner.unit_of_work() as session:
            await session.execute(
                text(
                    "UPDATE app.source_versions SET review_state = :s, reviewed_at = now() WHERE id = :id"
                ),
                {"s": end, "id": version},
            )

    if allowed:
        await move()
    else:
        assert await sqlstate_of(move) == IMMUTABLE


async def test_source_rows_reject_non_public_classes_and_bad_urls(owner: Plain) -> None:
    for bad in ("community_report_unverified", "ai_generated_explanation"):

        async def add(cls: str = bad) -> None:
            async with owner.unit_of_work() as session:
                await insert_source(session, information_class=cls)

        assert await sqlstate_of(add) == CHECK_VIOLATION

    async def bad_url() -> None:
        async with owner.unit_of_work() as session:
            await insert_source(session, url="javascript:alert(1)")

    assert await sqlstate_of(bad_url) == CHECK_VIOLATION


# ---- exact, bounded citations ---------------------------------------------------------------


async def test_a_citation_must_quote_the_version_exactly_at_its_offset(owner: Plain) -> None:
    _source, version = await approved_version(owner)
    async with owner.unit_of_work() as session:
        project = await insert_project(session)
        claim = await insert_claim(session, "fact", project)
        await insert_citation(session, "fact", claim, version)

    async def cite(passage: str, start: int, label: str = "p1") -> None:
        async with owner.unit_of_work() as session:
            await session.execute(
                text(
                    "INSERT INTO app.fact_citations VALUES (gen_random_uuid(), :c, :v, :p, :l, :s, now())"
                ),
                {"c": claim, "v": version, "p": passage, "l": label, "s": start},
            )

    assert (
        await sqlstate_of(lambda: cite("The synthetic clinic opened on 2 March.", 19))
        == CHECK_VIOLATION
    )
    assert await sqlstate_of(lambda: cite("synthetic", 0, "p2")) == CHECK_VIOLATION
    assert await sqlstate_of(lambda: cite("", 0, "p3")) == CHECK_VIOLATION
    assert await sqlstate_of(lambda: cite("x" * 1001, 0, "p4")) == CHECK_VIOLATION
    assert await sqlstate_of(lambda: cite("Synthetic", -1, "p5")) == CHECK_VIOLATION
    assert await sqlstate_of(lambda: cite("Synthetic", 0, "")) == CHECK_VIOLATION


# ---- the database backstop for public claims -------------------------------------------------


async def publish_directly(owner: Plain, kind: str, claim: uuid.UUID) -> None:
    table = "project_facts" if kind == "fact" else "project_updates"
    async with owner.unit_of_work() as session:
        await session.execute(
            text(
                f"UPDATE app.{table} SET visibility = 'public', published_at = now(), "
                "verification_state = 'verified_official' WHERE id = :id"
            ),
            {"id": claim},
        )


@pytest.mark.parametrize("kind", ["fact", "update"])
async def test_raw_publication_without_an_approved_citation_fails_at_commit(
    owner: Plain, kind: str
) -> None:
    async with owner.unit_of_work() as session:
        project = await insert_project(session)
        source = await insert_source(session)
        pending = await insert_version(session, source, state="pending")
        bare = await insert_claim(session, kind, project)
        weak = await insert_claim(session, kind, project)
        await insert_citation(session, kind, weak, pending)
    assert await sqlstate_of(lambda: publish_directly(owner, kind, bare)) == CHECK_VIOLATION
    assert await sqlstate_of(lambda: publish_directly(owner, kind, weak)) == CHECK_VIOLATION


@pytest.mark.parametrize("kind", ["fact", "update"])
async def test_raw_publication_with_an_approved_citation_succeeds_and_is_then_protected(
    owner: Plain, kind: str
) -> None:
    _source, version = await approved_version(owner)
    async with owner.unit_of_work() as session:
        project = await insert_project(session)
        claim = await insert_claim(session, kind, project)
        await insert_citation(session, kind, claim, version)
    await publish_directly(owner, kind, claim)

    async def remove_citation() -> None:
        async with owner.unit_of_work() as session:
            table = "fact_citations" if kind == "fact" else "update_citations"
            await session.execute(text(f"DELETE FROM app.{table}"), {}) if False else None
            await session.execute(
                text(f"DELETE FROM app.{table} WHERE source_version_id = :v"),
                {"v": version},
            )

    assert await sqlstate_of(remove_citation) == CHECK_VIOLATION

    async def reopen_version() -> None:
        async with owner.unit_of_work() as session:
            await session.execute(
                text("UPDATE app.source_versions SET review_state = 'in_review' WHERE id = :v"),
                {"v": version},
            )

    assert await sqlstate_of(reopen_version) == CHECK_VIOLATION


async def test_a_superseded_version_still_supports_history_but_a_second_citation_frees_a_reopen(
    owner: Plain,
) -> None:
    source, first = await approved_version(owner)
    async with owner.unit_of_work() as session:
        second = await insert_version(session, source, content=LATER_DOCUMENT)
        project = await insert_project(session)
        claim = await insert_claim(session, "fact", project)
        await insert_citation(session, "fact", claim, first)
        await insert_citation(session, "fact", claim, second)
    await publish_directly(owner, "fact", claim)
    async with owner.unit_of_work() as session:
        await session.execute(
            text("UPDATE app.source_versions SET review_state = 'superseded' WHERE id = :v"),
            {"v": first},
        )
        await session.execute(
            text("UPDATE app.source_versions SET review_state = 'in_review' WHERE id = :v"),
            {"v": second},
        ) if False else None
    async with owner.unit_of_work() as session:  # the superseded first version still counts
        await session.execute(
            text("UPDATE app.source_versions SET review_state = 'in_review' WHERE id = :v"),
            {"v": second},
        )


async def test_a_public_claim_needs_a_visible_date_and_a_real_verification_state(
    owner: Plain,
) -> None:
    async with owner.unit_of_work() as session:
        project = await insert_project(session)
        undated = await insert_claim(session, "fact", project, effective=None)

    async def undated_public() -> None:
        async with owner.unit_of_work() as session:
            await session.execute(
                text(
                    "UPDATE app.project_facts SET visibility = 'public', published_at = now(), "
                    "verification_state = 'verified_official' WHERE id = :id"
                ),
                {"id": undated},
            )

    assert await sqlstate_of(undated_public) == CHECK_VIOLATION

    async def awaiting_public() -> None:
        async with owner.unit_of_work() as session:
            await insert_claim(
                session,
                "fact",
                project,
                visibility="public",
                published=START,
                state="awaiting_verification",
            )

    assert await sqlstate_of(awaiting_public) == CHECK_VIOLATION


# ---- the publication service ---------------------------------------------------------------


async def service_publish(owner: Plain, kind: str, claim: uuid.UUID, state: str) -> object:
    async with owner.unit_of_work() as session:
        return await PublicationService(session, ManualClock(START)).publish(
            kind,  # type: ignore[arg-type]  # parametrised with "fact" or "update"
            claim,
            verification_state=state,
        )


async def gaps_of(owner: Plain, kind: str, claim: uuid.UUID, state: str) -> set[tuple[str, str]]:
    with pytest.raises(ProblemError) as raised:
        await service_publish(owner, kind, claim, state)
    assert raised.value.problem is PUBLICATION_INCOMPLETE
    return {(e.field, e.code) for e in raised.value.field_errors}


async def visibility_of(owner: Plain, kind: str, claim: uuid.UUID) -> str:
    table = "project_facts" if kind == "fact" else "project_updates"
    async with owner.unit_of_work() as session:
        return (
            await session.execute(
                text(f"SELECT visibility FROM app.{table} WHERE id = :id"), {"id": claim}
            )
        ).scalar_one()


@pytest.mark.parametrize("kind", ["fact", "update"])
async def test_the_service_names_every_gap_and_leaves_the_draft_untouched(
    owner: Plain, kind: str
) -> None:
    async with owner.unit_of_work() as session:
        project = await insert_project(session)
        source = await insert_source(session)
        pending = await insert_version(session, source, state="pending")
        rejected = await insert_version(session, source, content=LATER_DOCUMENT, state="rejected")
        bare = await insert_claim(session, kind, project, effective=None)
        weak = await insert_claim(session, kind, project)
        await insert_citation(session, kind, weak, pending)
        await insert_citation(session, kind, weak, rejected)
    assert await gaps_of(owner, kind, bare, "awaiting_verification") == {
        ("citations", "approved_citation_required"),
        ("dates", "visible_date_required"),
        ("verification_state", "verification_required"),
    }
    assert await gaps_of(owner, kind, weak, "verified_official") == {
        ("citations", "approved_citation_required"),
        ("verification_state", "official_source_required"),
    }
    assert await visibility_of(owner, kind, bare) == "draft"
    assert await visibility_of(owner, kind, weak) == "draft"


async def test_verification_states_carry_their_own_evidence_rules(owner: Plain) -> None:
    async with owner.unit_of_work() as session:
        project = await insert_project(session)
        media = await insert_source(
            session, information_class="independent_source", publisher="Synthetic Press"
        )
        media_version = await insert_version(session, media)
        same_publisher = await insert_source(
            session, information_class="independent_source", publisher="Synthetic Press"
        )
        same_version = await insert_version(session, same_publisher)
        other = await insert_source(
            session, information_class="independent_source", publisher="Other Press"
        )
        other_version = await insert_version(session, other)
        claim = await insert_claim(session, "fact", project)
        await insert_citation(session, "fact", claim, media_version)
    assert await gaps_of(owner, "fact", claim, "verified_official") == {
        ("verification_state", "official_source_required")
    }
    assert await gaps_of(owner, "fact", claim, "corroborated") == {
        ("verification_state", "independent_sources_required")
    }
    assert await gaps_of(owner, "fact", claim, "community_reviewed") == {
        ("verification_state", "reviewed_community_evidence_required")
    }
    async with owner.unit_of_work() as session:
        await insert_citation(session, "fact", claim, same_version, label="other page")
    assert await gaps_of(owner, "fact", claim, "corroborated") == {
        ("verification_state", "independent_sources_required")
    }, "two sources from one publisher are not independent"
    async with owner.unit_of_work() as session:
        await insert_citation(session, "fact", claim, other_version, label="p3")
    published = await service_publish(owner, "fact", claim, "corroborated")
    assert published.published_at == START  # type: ignore[attr-defined]


@pytest.mark.parametrize("kind", ["fact", "update"])
async def test_a_complete_item_publishes_with_the_injected_time(owner: Plain, kind: str) -> None:
    _source, version = await approved_version(owner)
    async with owner.unit_of_work() as session:
        project = await insert_project(session)
        claim = await insert_claim(session, kind, project)
        await insert_citation(session, kind, claim, version)
    await service_publish(owner, kind, claim, "verified_official")
    assert await visibility_of(owner, kind, claim) == "public"


async def test_publishing_an_unknown_item_is_the_generic_not_found(owner: Plain) -> None:
    with pytest.raises(ProblemError) as raised:
        await service_publish(owner, "fact", uuid.uuid4(), "verified_official")
    assert raised.value.problem is NOT_FOUND


# ---- what the public role can see ------------------------------------------------------------


async def test_public_views_show_only_published_cited_material_and_no_tables(
    owner: Plain, public: Database
) -> None:
    source, version = await approved_version(owner)
    async with owner.unit_of_work() as session:
        project = await insert_project(session)
        shown = await insert_claim(session, "fact", project)
        draft = await insert_claim(session, "fact", project)
        await insert_citation(session, "fact", shown, version)
        await insert_citation(session, "fact", draft, version, label="p9")
        unrelated = await insert_source(session)
        await insert_version(session, unrelated)
    await service_publish(owner, "fact", shown, "verified_official")
    async with public.unit_of_work() as session:
        facts = {
            r.id for r in await session.execute(text("SELECT id FROM public_api.project_facts"))
        }
        cite_result = await session.execute(
            text("SELECT * FROM public_api.fact_citations WHERE fact_id = :f"), {"f": shown}
        )
        cite_columns = set(cite_result.keys())
        cites = cite_result.all()
        sources = {
            r.id for r in await session.execute(text("SELECT id FROM public_api.cited_sources"))
        }
        draft_cites = (
            await session.execute(
                text("SELECT 1 FROM public_api.fact_citations WHERE fact_id = :f"), {"f": draft}
            )
        ).all()
    assert shown in facts
    assert draft not in facts
    assert draft_cites == []
    assert len(cites) == 1
    assert cites[0].passage == "The synthetic clinic opened on 1 March."
    assert cites[0].source_id == source
    assert source in sources
    assert unrelated not in sources
    assert not cite_columns & {"content_text", "review_state", "source_version_id"}
    for table in ("app.sources", "app.source_versions", "app.project_facts", "app.fact_citations"):

        async def read(name: str = table) -> None:
            async with public.unit_of_work() as session:
                await session.execute(text(f"SELECT * FROM {name}"))

        assert await sqlstate_of(read) == PRIVILEGE
