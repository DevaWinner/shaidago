"""Escalation routes: cited and dated, locale-honest, validity-windowed, never invented."""

import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import date

import pytest
from sqlalchemy import text
from sqlalchemy.engine import URL
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from shaidago.projects.escalation import EscalationRepository
from shaidago.shared.database import Database, build_engine
from tests.integration.support import (
    LOCALITY,
    NOW,
    Plain,
    insert_project,
    insert_source,
    insert_version,
)

CHECK_VIOLATION = "23514"
UNIQUE_VIOLATION = "23505"
PRIVILEGE = "42501"
TODAY = date(2026, 9, 19)


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


async def locality_slug(session: AsyncSession) -> str:
    await insert_project(session)  # ensures the synthetic locality exists
    return (
        await session.execute(
            text("SELECT slug FROM app.localities WHERE id = :id"), {"id": LOCALITY}
        )
    ).scalar_one()


async def add_route(
    session: AsyncSession,
    version: uuid.UUID,
    **overrides: object,
) -> None:
    fields: dict[str, object] = {
        "category": None,
        "locale": "en",
        "organisation": f"Synthetic Office {uuid.uuid4().hex[:6]}",
        "instructions": "Synthetic instructions: contact the synthetic office.",
        "disclaimer": "Synthetic disclaimer: this is not an emergency service.",
        "verified": date(2026, 9, 1),
        "valid_from": date(2026, 9, 1),
        "valid_to": None,
        "active": True,
    } | overrides
    await session.execute(
        text(
            "INSERT INTO app.escalation_routes VALUES (gen_random_uuid(), :loc, :cat, :locale, "
            ":org, :ins, :dis, :ver, :verified, :vf, :vt, :active, :now, :now)"
        ),
        {
            "loc": LOCALITY,
            "cat": fields["category"],
            "locale": fields["locale"],
            "org": fields["organisation"],
            "ins": fields["instructions"],
            "dis": fields["disclaimer"],
            "ver": version,
            "verified": fields["verified"],
            "vf": fields["valid_from"],
            "vt": fields["valid_to"],
            "active": fields["active"],
            "now": NOW,
        },
    )


async def approved_version(session: AsyncSession, state: str = "approved") -> uuid.UUID:
    source = await insert_source(session)
    return await insert_version(session, source, state=state)


async def test_a_locality_with_no_verified_route_gets_an_empty_list_never_a_default(
    public: Database,
) -> None:
    async with public.unit_of_work() as session:
        routes = await EscalationRepository(session).routes_for(
            "synthetic-locality-without-routes", "unsafe_construction", "en", today=TODAY
        )
    assert routes == []


async def test_an_active_route_must_cite_an_approved_source_version(owner: Plain) -> None:
    async with owner.unit_of_work() as session:
        await locality_slug(session)
        pending = await approved_version(session, "pending")
        rejected = await approved_version(session, "rejected")
        approved = await approved_version(session)
        superseded = await approved_version(session, "superseded")

    for bad in (pending, rejected):

        async def add(version: uuid.UUID = bad) -> None:
            async with owner.unit_of_work() as session:
                await add_route(session, version)

        assert await sqlstate_of(add) == CHECK_VIOLATION
    for good in (approved, superseded):
        async with owner.unit_of_work() as session:
            await add_route(session, good)

    async def inactive_draft() -> None:
        async with owner.unit_of_work() as session:
            await add_route(session, pending, active=False)

    await inactive_draft()  # an inactive draft may cite anything while it awaits review


async def test_route_constraints(owner: Plain) -> None:
    async with owner.unit_of_work() as session:
        await locality_slug(session)
        version = await approved_version(session)

    async def add(**fields: object) -> None:
        async with owner.unit_of_work() as session:
            await add_route(session, version, **fields)

    assert await sqlstate_of(lambda: add(category="fraud")) == CHECK_VIOLATION
    assert await sqlstate_of(lambda: add(locale="fr")) == CHECK_VIOLATION
    assert await sqlstate_of(lambda: add(disclaimer="")) == CHECK_VIOLATION
    assert await sqlstate_of(lambda: add(instructions="")) == CHECK_VIOLATION
    assert await sqlstate_of(lambda: add(organisation="")) == CHECK_VIOLATION
    assert await sqlstate_of(lambda: add(instructions="x" * 2001)) == CHECK_VIOLATION
    assert (
        await sqlstate_of(lambda: add(valid_from=date(2026, 9, 10), valid_to=date(2026, 9, 1)))
        == CHECK_VIOLATION
    )
    assert await sqlstate_of(lambda: add(verified=date(2026, 9, 20))) == CHECK_VIOLATION
    for category in ("no_visible_work", "unsafe_construction", "other_concern", None):
        await add(category=category)


async def test_one_route_per_locality_category_locale_and_organisation_even_without_category(
    owner: Plain,
) -> None:
    async with owner.unit_of_work() as session:
        await locality_slug(session)
        version = await approved_version(session)
    organisation = f"Synthetic Office {uuid.uuid4().hex}"

    async def add(category: str | None) -> None:
        async with owner.unit_of_work() as session:
            await add_route(session, version, organisation=organisation, category=category)

    await add(None)
    assert await sqlstate_of(lambda: add(None)) == UNIQUE_VIOLATION
    await add("access_barrier")
    assert await sqlstate_of(lambda: add("access_barrier")) == UNIQUE_VIOLATION


async def test_lookup_honours_the_validity_window_and_active_flag_and_orders_by_specificity(
    owner: Plain, public: Database
) -> None:
    async with owner.unit_of_work() as session:
        slug = await locality_slug(session)
        version = await approved_version(session)
        await add_route(session, version, organisation="Aaa General", category=None)
        await add_route(
            session, version, organisation="Zzz Specific", category="unsafe_construction"
        )
        await add_route(
            session,
            version,
            organisation="Expired",
            valid_from=date(2025, 1, 1),
            valid_to=date(2026, 1, 1),
        )
        await add_route(session, version, organisation="Future", valid_from=date(2027, 1, 1))
        await add_route(session, version, organisation="Switched Off", active=False)
        await add_route(session, version, organisation="Other Concern", category="access_barrier")
    async with public.unit_of_work() as session:
        routes = await EscalationRepository(session).routes_for(
            slug, "unsafe_construction", "en", today=TODAY
        )
    names = [r.organisation for r in routes]
    assert {"Aaa General", "Zzz Specific"} <= set(names)
    assert not {"Expired", "Future", "Switched Off", "Other Concern"} & set(names)
    assert names.index("Zzz Specific") < names.index("Aaa General"), "specific before general"


async def test_lookup_serves_the_requested_locale_and_labels_english_fallback(
    owner: Plain, public: Database
) -> None:
    async with owner.unit_of_work() as session:
        slug = await locality_slug(session)
        version = await approved_version(session)
        await add_route(
            session, version, organisation="Both Locales", locale="en", instructions="English text"
        )
        await add_route(
            session, version, organisation="Both Locales", locale="ha", instructions="Hausa text"
        )
        await add_route(
            session, version, organisation="English Only", locale="en", instructions="English only"
        )
    async with public.unit_of_work() as session:
        routes = {
            r.organisation: r
            for r in await EscalationRepository(session).routes_for(
                slug, "other_concern", "ha", today=TODAY
            )
        }
    assert (routes["Both Locales"].served_locale, routes["Both Locales"].is_fallback) == (
        "ha",
        False,
    )
    assert routes["Both Locales"].instructions == "Hausa text"
    assert (routes["English Only"].served_locale, routes["English Only"].is_fallback) == (
        "en",
        True,
    )
    for route in routes.values():
        assert route.disclaimer
        assert route.source_url.startswith("https://")
        assert route.verified_on <= TODAY


async def test_public_role_reads_only_the_view_and_the_view_leaks_no_internal_ids(
    owner: Plain, public: Database
) -> None:
    async with owner.unit_of_work() as session:
        await locality_slug(session)
        await add_route(session, await approved_version(session))
    async with public.unit_of_work() as session:
        result = await session.execute(text("SELECT * FROM public_api.escalation_routes"))
        columns = set(result.keys())
    assert not columns & {"source_version_id", "locality_id", "active", "created_at", "updated_at"}

    async def read_table() -> None:
        async with public.unit_of_work() as session:
            await session.execute(text("SELECT * FROM app.escalation_routes"))

    assert await sqlstate_of(read_table) == PRIVILEGE


async def test_the_table_has_no_contact_detail_columns(owner: Plain) -> None:
    async with owner.unit_of_work() as session:
        columns = {
            r[0]
            for r in await session.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema = 'app' AND table_name = 'escalation_routes'"
                )
            )
        }
    assert not any(
        word in name for name in columns for word in ("phone", "address", "email", "tel")
    )
