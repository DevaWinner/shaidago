"""Constraints, the deferred source-text rule, role access, and the public projection.

All rows are synthetic (`synthetic-*`); nothing here is a claim about a real project. Constraint
assertions use an untranslated session so the raw SQLSTATE is visible.
"""

import uuid
from collections.abc import AsyncGenerator, AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.engine import URL
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from shaidago.projects.repository import PublicProjectRepository
from shaidago.shared.database import Database, build_engine
from shaidago.shared.vocabulary import values

NOW = datetime(2026, 9, 19, 12, 0, tzinfo=UTC)
PARENT = uuid.UUID("018f0000-0000-7000-8000-000000000001")
CHILD = uuid.UUID("018f0000-0000-7000-8000-000000000002")
CHECK_VIOLATION = "23514"
UNIQUE_VIOLATION = "23505"
RESTRICT_VIOLATION = "23001"
PRIVILEGE = "42501"
EN_ONLY = (("en", "reviewed"),)
EN_AND_HAUSA = (("en", "reviewed"), ("ha", "machine_assisted"))
PROJECT_COLUMNS = {
    "id",
    "slug",
    "locality_slug",
    "category",
    "public_status",
    "last_checked_on",
    "updated_at",
}


class Plain:
    """One transaction per block on an engine, with no error translation."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._sessions = async_sessionmaker(engine, expire_on_commit=False)

    @asynccontextmanager
    async def unit_of_work(self) -> AsyncGenerator[AsyncSession]:
        async with self._sessions() as session, session.begin():
            yield session


@pytest.fixture
async def owner(role_urls: dict[str, URL]) -> AsyncIterator[Plain]:
    engine = build_engine(role_urls["owner"], application_name="owner", statement_timeout_ms=8000)
    plain = Plain(engine)
    async with plain.unit_of_work() as session:
        for table in ("project_translations", "projects", "localities"):
            await session.execute(text(f"DELETE FROM app.{table}"))
        await session.execute(
            text(
                "INSERT INTO app.localities VALUES (:a, 'synthetic-state', 'Synthetic State', "
                "'state', NULL, ARRAY['en','ha','ig','yo'], :now, :now), "
                "(:b, 'synthetic-council', 'Synthetic Council', 'area_council', :a, "
                "ARRAY['en','ha'], :now, :now)"
            ),
            {"a": PARENT, "b": CHILD, "now": NOW},
        )
    yield plain
    await engine.dispose()


@pytest.fixture
async def public(role_urls: dict[str, URL]) -> AsyncIterator[Database]:
    engine = build_engine(
        role_urls["shaidago_public"], application_name="public", statement_timeout_ms=8000
    )
    yield Database(engine)
    await engine.dispose()


async def add_translation(
    session: AsyncSession, project_id: uuid.UUID, locale: str, status: str
) -> None:
    await session.execute(
        text(
            "INSERT INTO app.project_translations VALUES (:id, :pid, :loc, :title, :summary, "
            ":promise, :status, :reviewed, NULL, :now, :now)"
        ),
        {
            "id": uuid.uuid4(),
            "pid": project_id,
            "loc": locale,
            "title": f"synthetic title ({locale})",
            "summary": f"synthetic summary ({locale})",
            "promise": f"synthetic deliverable ({locale})",
            "status": status,
            "reviewed": NOW if status == "reviewed" else None,
            "now": NOW,
        },
    )


async def add_project(db: Plain, slug: str, **overrides: Any) -> uuid.UUID:
    fields: dict[str, Any] = {
        "visibility": "public",
        "translations": EN_ONLY,
        "category": "health",
        "status": "planned",
        "checked": None,
    } | overrides
    project_id = uuid.uuid4()
    async with db.unit_of_work() as session:
        await session.execute(
            text(
                "INSERT INTO app.projects VALUES (:id, :slug, :loc, :cat, :status, :vis, "
                "CAST(:checked AS date), :now, :now)"
            ),
            {
                "id": project_id,
                "slug": slug,
                "loc": CHILD,
                "cat": fields["category"],
                "status": fields["status"],
                "vis": fields["visibility"],
                "checked": fields["checked"],
                "now": NOW,
            },
        )
        for locale, translation_status in fields["translations"]:
            await add_translation(session, project_id, locale, translation_status)
    return project_id


async def sqlstate_of(action: Callable[[], Awaitable[object]]) -> str | None:
    with pytest.raises(DBAPIError) as raised:
        await action()
    return getattr(raised.value.orig, "sqlstate", None)


def selecting(db: Database, table: str) -> Callable[[], Awaitable[None]]:
    async def run() -> None:
        async with db.unit_of_work() as session:
            await session.execute(text(f"SELECT * FROM {table}"))

    return run


async def test_slugs_are_unique_and_lowercase_kebab_case(owner: Plain) -> None:
    await add_project(owner, "synthetic-clinic")
    assert await sqlstate_of(lambda: add_project(owner, "synthetic-clinic")) == UNIQUE_VIOLATION
    for bad in ("Synthetic", "with space", "-leading", "trailing-", "double--dash", ""):
        assert await sqlstate_of(lambda bad=bad: add_project(owner, bad)) == CHECK_VIOLATION


@pytest.mark.parametrize(
    ("field", "bad"), [("category", "roads"), ("status", "abandoned"), ("visibility", "private")]
)
async def test_vocabulary_columns_reject_values_outside_the_contract(
    owner: Plain, field: str, bad: str
) -> None:
    state = await sqlstate_of(lambda: add_project(owner, "synthetic-bad", **{field: bad}))
    assert state == CHECK_VIOLATION


async def test_every_contract_value_is_accepted(owner: Plain) -> None:
    for index, category in enumerate(values("project_category")):
        await add_project(owner, f"synthetic-category-{index}", category=category)
    for index, status in enumerate(values("project_public_status")):
        await add_project(owner, f"synthetic-status-{index}", status=status)


async def test_last_checked_cannot_be_after_the_row_was_written(owner: Plain) -> None:
    await add_project(owner, "synthetic-checked", checked="2026-09-19")
    future = await sqlstate_of(lambda: add_project(owner, "synthetic-future", checked="2026-09-20"))
    assert future == CHECK_VIOLATION


async def test_locality_locales_must_be_supported_and_include_english(owner: Plain) -> None:
    async def insert(locales: str) -> None:
        async with owner.unit_of_work() as session:
            await session.execute(
                text(
                    "INSERT INTO app.localities VALUES (gen_random_uuid(), :slug, 'n', 'state', "
                    f"NULL, {locales}, :now, :now)"
                ),
                {"slug": f"synthetic-{uuid.uuid4().hex[:6]}", "now": NOW},
            )

    assert await sqlstate_of(lambda: insert("ARRAY['en','fr']")) == CHECK_VIOLATION
    assert await sqlstate_of(lambda: insert("ARRAY['ha']")) == CHECK_VIOLATION
    await insert("ARRAY['en','yo']")


async def test_translation_rules(owner: Plain) -> None:
    project = await add_project(owner, "synthetic-translations")

    async def add(locale: str, status: str) -> None:
        async with owner.unit_of_work() as session:
            await add_translation(session, project, locale, status)

    async def raw(locale: str, title: str, status: str, reviewed: str) -> None:
        async with owner.unit_of_work() as session:
            await session.execute(
                text(
                    "INSERT INTO app.project_translations VALUES (gen_random_uuid(), :p, "
                    f":loc, :title, 's', 'd', :status, {reviewed}, NULL, :now, :now)"
                ),
                {"p": project, "loc": locale, "title": title, "status": status, "now": NOW},
            )

    assert await sqlstate_of(lambda: add("en", "reviewed")) == UNIQUE_VIOLATION
    assert await sqlstate_of(lambda: add("fr", "reviewed")) == CHECK_VIOLATION
    assert await sqlstate_of(lambda: add("ha", "approved")) == CHECK_VIOLATION
    await add("ha", "machine_assisted")
    assert await sqlstate_of(lambda: raw("ig", "t", "reviewed", "NULL")) == CHECK_VIOLATION
    assert await sqlstate_of(lambda: raw("yo", "", "machine_assisted", "NULL")) == CHECK_VIOLATION


async def test_locality_delete_is_restricted_and_project_delete_cascades(owner: Plain) -> None:
    project = await add_project(owner, "synthetic-cascade")

    async def delete_locality() -> None:
        async with owner.unit_of_work() as session:
            await session.execute(text("DELETE FROM app.localities WHERE id = :id"), {"id": CHILD})

    assert await sqlstate_of(delete_locality) == RESTRICT_VIOLATION
    async with owner.unit_of_work() as session:
        await session.execute(text("DELETE FROM app.projects WHERE id = :id"), {"id": project})
        left = await session.execute(
            text("SELECT count(*) FROM app.project_translations WHERE project_id = :id"),
            {"id": project},
        )
        assert left.scalar_one() == 0


async def test_a_public_project_needs_english_source_text_at_commit(owner: Plain) -> None:
    no_text = await sqlstate_of(lambda: add_project(owner, "synthetic-no-text", translations=()))
    only_hausa = await sqlstate_of(
        lambda: add_project(owner, "synthetic-only-hausa", translations=(("ha", "reviewed"),))
    )
    unavailable = await sqlstate_of(
        lambda: add_project(owner, "synthetic-unavailable", translations=(("en", "unavailable"),))
    )
    assert (no_text, only_hausa, unavailable) == (CHECK_VIOLATION,) * 3
    await add_project(owner, "synthetic-hidden-no-text", visibility="hidden", translations=())
    await add_project(owner, "synthetic-ok", translations=EN_AND_HAUSA)


async def test_the_rule_also_guards_updates_and_deletes(owner: Plain) -> None:
    hidden = await add_project(owner, "synthetic-later", visibility="hidden", translations=())

    async def publish() -> None:
        async with owner.unit_of_work() as session:
            await session.execute(
                text("UPDATE app.projects SET visibility = 'public' WHERE id = :id"), {"id": hidden}
            )

    assert await sqlstate_of(publish) == CHECK_VIOLATION
    live = await add_project(owner, "synthetic-live")

    async def drop_english() -> None:
        async with owner.unit_of_work() as session:
            await session.execute(
                text(
                    "DELETE FROM app.project_translations WHERE project_id = :id AND locale = 'en'"
                ),
                {"id": live},
            )

    assert await sqlstate_of(drop_english) == CHECK_VIOLATION


async def test_public_role_sees_only_visible_translated_projects_through_views(
    owner: Plain, public: Database
) -> None:
    await add_project(owner, "synthetic-visible", translations=EN_AND_HAUSA)
    await add_project(owner, "synthetic-secret", visibility="hidden")
    async with public.unit_of_work() as session:
        result = await session.execute(text("SELECT * FROM public_api.projects"))
        assert set(result.keys()) == PROJECT_COLUMNS
        assert {row.slug for row in result} == {"synthetic-visible"}
    for table in ("app.projects", "app.project_translations", "app.localities"):
        assert await sqlstate_of(selecting(public, table)) == PRIVILEGE


async def test_repository_serves_the_requested_locale_and_labels_a_fallback_honestly(
    owner: Plain, public: Database
) -> None:
    await add_project(owner, "synthetic-multilingual", translations=EN_AND_HAUSA)
    async with public.unit_of_work() as session:
        repository = PublicProjectRepository(session)
        hausa = await repository.get_project("synthetic-multilingual", "ha")
        yoruba = await repository.get_project("synthetic-multilingual", "yo")
        english = await repository.get_project("synthetic-multilingual", "en")
    assert hausa is not None
    assert yoruba is not None
    assert english is not None
    assert (hausa.text.served_locale, hausa.text.is_fallback) == ("ha", False)
    assert hausa.text.translation_status == "machine_assisted"
    assert (yoruba.text.requested_locale, yoruba.text.served_locale) == ("yo", "en")
    assert yoruba.text.is_fallback
    assert yoruba.text.title == "synthetic title (en)"
    assert not english.text.is_fallback


async def test_absent_and_hidden_projects_are_indistinguishable(
    owner: Plain, public: Database
) -> None:
    await add_project(owner, "synthetic-hidden", visibility="hidden")
    async with public.unit_of_work() as session:
        repository = PublicProjectRepository(session)
        assert await repository.get_project("synthetic-hidden", "en") is None
        assert await repository.get_project("synthetic-never-existed", "en") is None


@pytest.mark.usefixtures("owner")
async def test_repository_lists_localities_with_parent_slugs(public: Database) -> None:
    async with public.unit_of_work() as session:
        localities = await PublicProjectRepository(session).list_localities()
    by_slug = {locality.slug: locality for locality in localities}
    assert by_slug["synthetic-state"].parent_slug is None
    assert by_slug["synthetic-council"].parent_slug == "synthetic-state"
    assert by_slug["synthetic-council"].enabled_locales == ("en", "ha")
    assert by_slug["synthetic-council"].kind == "area_council"


async def test_database_checks_contain_every_contract_value(owner: Plain) -> None:
    async with owner.unit_of_work() as session:
        rows = (
            await session.execute(
                text(
                    "SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint WHERE conname IN "
                    "('ck_projects_category', 'ck_projects_public_status', "
                    "'ck_project_translations_status')"
                )
            )
        ).all()
    definitions = {str(row[0]): str(row[1]) for row in rows}
    for name, vocabulary in (
        ("ck_projects_category", "project_category"),
        ("ck_projects_public_status", "project_public_status"),
        ("ck_project_translations_status", "translation_status"),
    ):
        for value in values(vocabulary):
            assert f"'{value}'" in definitions[name], (name, value)
        assert definitions[name].count("::text") == len(values(vocabulary))
