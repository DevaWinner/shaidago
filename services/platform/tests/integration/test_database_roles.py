"""Connects as every application role and asserts what it may and may not do (ADR-0003).

Probe tables stand in for the real ones so the grant model is proven before the domain exists.
Each later table migration must add its own grants and policies and its own allow/deny test.
"""

import asyncio
import uuid
from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime
from typing import Any

import psycopg
import pytest
from sqlalchemy import DateTime, String, Uuid, event, text
from sqlalchemy.engine import URL
from sqlalchemy.exc import DBAPIError, ProgrammingError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from shaidago.db.roles import APPLICATION_ROLES, apply_security_baseline, enable_login
from shaidago.shared.database import build_engine
from shaidago.shared.private_insert import PRIVATE_MAPPER_ARGS, PRIVATE_TABLE_ARGS
from tests.integration.conftest import disposable_database

INSUFFICIENT_PRIVILEGE = "42501"
UNDEFINED_COLUMN = "42703"
PASSWORD = "role-password-with-'quote-and-%-percent"

PROBE_DDL = """
SET ROLE shaidago_owner;
CREATE TABLE app.probe_reports (
    id uuid PRIMARY KEY, created_at timestamptz NOT NULL, body text NOT NULL,
    server_note text NOT NULL DEFAULT 'server-default');
ALTER TABLE app.probe_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.probe_reports FORCE ROW LEVEL SECURITY;
GRANT INSERT ON app.probe_reports TO shaidago_public;
GRANT SELECT, INSERT, UPDATE ON app.probe_reports TO shaidago_reviewer;
CREATE POLICY probe_public_insert ON app.probe_reports
    FOR INSERT TO shaidago_public WITH CHECK (true);
CREATE POLICY probe_reviewer_all ON app.probe_reports
    FOR ALL TO shaidago_reviewer USING (true) WITH CHECK (true);
CREATE TABLE app.probe_contacts (id uuid PRIMARY KEY, value text NOT NULL);
INSERT INTO app.probe_contacts VALUES (gen_random_uuid(), 'private-contact');
CREATE TABLE app.probe_projects (id int PRIMARY KEY, name text NOT NULL, internal_note text);
INSERT INTO app.probe_projects VALUES (1, 'Public project', 'internal only');
CREATE VIEW public_api.probe_projects AS SELECT id, name FROM app.probe_projects;
RESET ROLE;
"""


class Base(DeclarativeBase):
    pass


class ReportRow(Base):
    """Follows the private-insert rules: client-side ID and timestamp, no read-back."""

    __tablename__ = "probe_reports"
    __table_args__ = PRIVATE_TABLE_ARGS
    __mapper_args__ = PRIVATE_MAPPER_ARGS
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    body: Mapped[str] = mapped_column(String)


NAIVE_TABLE_ARGS: dict[str, Any] = {"schema": "app", "extend_existing": True}
NAIVE_MAPPER_ARGS: dict[str, Any] = {"eager_defaults": True}


class NaiveReportRow(Base):
    """Control: default ORM behaviour, which reads server defaults back with RETURNING."""

    __tablename__ = "probe_reports"
    __table_args__ = NAIVE_TABLE_ARGS
    __mapper_args__ = NAIVE_MAPPER_ARGS
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    body: Mapped[str] = mapped_column(String)
    server_note: Mapped[str] = mapped_column(String, server_default="server-default")


@pytest.fixture(scope="module")
def role_urls(
    admin_connection: psycopg.Connection[tuple[object, ...]],
) -> Iterator[dict[str, URL]]:
    with disposable_database(admin_connection) as owner_url:

        async def prepare() -> None:
            engine = build_engine(owner_url, application_name="setup", statement_timeout_ms=10000)
            try:
                async with engine.begin() as connection:
                    await apply_security_baseline(connection)
                    await connection.exec_driver_sql(PROBE_DDL)
                    for role in APPLICATION_ROLES:
                        await enable_login(connection, role, PASSWORD)
            finally:
                await engine.dispose()

        asyncio.run(prepare())
        urls = {role: owner_url.set(username=role, password=PASSWORD) for role in APPLICATION_ROLES}
        urls["owner"] = owner_url
        yield urls


@pytest.fixture
async def engines(role_urls: dict[str, URL]) -> AsyncIterator[dict[str, AsyncEngine]]:
    built = {
        name: build_engine(url, application_name=f"role-{name}", statement_timeout_ms=5000)
        for name, url in role_urls.items()
    }
    yield built
    for engine in built.values():
        await engine.dispose()


async def run(engine: AsyncEngine, statement: str) -> list[tuple[object, ...]]:
    async with engine.begin() as connection:
        result = await connection.execute(text(statement))
        return [tuple(row) for row in result.fetchall()] if result.returns_rows else []


async def denied(
    engine: AsyncEngine, statement: str, sqlstate: str = INSUFFICIENT_PRIVILEGE
) -> None:
    with pytest.raises(DBAPIError) as raised:
        await run(engine, statement)
    assert getattr(raised.value.orig, "sqlstate", None) == sqlstate


def report_insert(row_id: uuid.UUID | None = None) -> str:
    return (
        f"INSERT INTO app.probe_reports (id, created_at, body) "
        f"VALUES ('{row_id or uuid.uuid4()}', now(), 'text')"
    )


async def test_application_roles_are_not_privileged_and_login_needs_a_password(
    engines: dict[str, AsyncEngine],
) -> None:
    for role in APPLICATION_ROLES:
        [(superuser, bypass, createdb, createrole)] = await run(
            engines[role],
            "SELECT rolsuper, rolbypassrls, rolcreatedb, rolcreaterole "
            "FROM pg_roles WHERE rolname = current_user",
        )
        assert (superuser, bypass, createdb, createrole) == (False, False, False, False)
        assert await run(engines[role], "SELECT current_user") == [(role,)]


async def test_public_role_may_insert_reports_but_never_read_or_change_them(
    engines: dict[str, AsyncEngine],
) -> None:
    public = engines["shaidago_public"]
    await run(public, report_insert())
    await denied(public, "SELECT id FROM app.probe_reports")
    await denied(public, "SELECT count(*) FROM app.probe_reports")
    await denied(public, "UPDATE app.probe_reports SET body = 'x'")
    await denied(public, "DELETE FROM app.probe_reports")
    await denied(public, report_insert() + " RETURNING id")


async def test_public_role_reaches_only_the_public_view_and_only_its_columns(
    engines: dict[str, AsyncEngine],
) -> None:
    public = engines["shaidago_public"]
    assert await run(public, "SELECT id, name FROM public_api.probe_projects") == [
        (1, "Public project")
    ]
    await denied(public, "SELECT internal_note FROM public_api.probe_projects", UNDEFINED_COLUMN)
    await denied(public, "SELECT * FROM app.probe_projects")
    await denied(public, "SELECT * FROM app.probe_contacts")
    await denied(public, "INSERT INTO public_api.probe_projects VALUES (2, 'x')")
    await denied(public, "SELECT * FROM pg_authid")


async def test_public_role_cannot_create_objects_or_escalate(
    engines: dict[str, AsyncEngine],
) -> None:
    public = engines["shaidago_public"]
    await denied(public, "CREATE TABLE public.injected (id int)")
    await denied(public, "CREATE TABLE app.injected (id int)")
    await denied(public, "CREATE TABLE public_api.injected (id int)")
    await denied(public, "SET ROLE shaidago_owner", "42501")
    await denied(public, "ALTER ROLE shaidago_public SUPERUSER")


async def test_reviewer_can_read_insert_and_update_reports_but_not_delete_or_read_contacts(
    engines: dict[str, AsyncEngine],
) -> None:
    reviewer = engines["shaidago_reviewer"]
    await run(reviewer, report_insert())
    [(visible,)] = await run(reviewer, "SELECT count(*) FROM app.probe_reports")
    assert isinstance(visible, int)
    assert visible >= 1
    await run(reviewer, "UPDATE app.probe_reports SET body = 'reviewed'")
    await denied(reviewer, "DELETE FROM app.probe_reports")
    await denied(reviewer, "SELECT * FROM app.probe_contacts")
    await denied(reviewer, "DROP TABLE app.probe_reports")


async def test_worker_and_ops_roles_cannot_touch_private_tables(
    engines: dict[str, AsyncEngine],
) -> None:
    for role in ("shaidago_worker", "shaidago_readonly_ops"):
        for statement in (
            "SELECT * FROM app.probe_reports",
            "SELECT * FROM app.probe_contacts",
            "SELECT * FROM app.probe_projects",
            report_insert(),
        ):
            await denied(engines[role], statement)
    assert await run(engines["shaidago_worker"], "SELECT name FROM public_api.probe_projects")
    # Ops receive no view by default; each aggregate view is granted explicitly when it exists.
    await denied(engines["shaidago_readonly_ops"], "SELECT * FROM public_api.probe_projects")


async def test_row_security_denies_when_a_select_grant_exists_without_a_policy(
    engines: dict[str, AsyncEngine],
) -> None:
    owner = engines["owner"]
    await run(owner, "GRANT SELECT ON app.probe_reports TO shaidago_worker")
    try:
        assert await run(engines["shaidago_reviewer"], "SELECT count(*) FROM app.probe_reports")
        assert await run(engines["shaidago_worker"], "SELECT * FROM app.probe_reports") == []
    finally:
        await run(owner, "REVOKE SELECT ON app.probe_reports FROM shaidago_worker")


async def test_baseline_is_idempotent(role_urls: dict[str, URL]) -> None:
    engine = build_engine(role_urls["owner"], application_name="again", statement_timeout_ms=10000)
    try:
        async with engine.begin() as connection:
            await apply_security_baseline(connection)
            await apply_security_baseline(connection)
    finally:
        await engine.dispose()


async def test_enable_login_rejects_unknown_roles_and_weak_passwords(
    engines: dict[str, AsyncEngine],
) -> None:
    async with engines["owner"].begin() as connection:
        with pytest.raises(ValueError, match="not an application role"):
            await enable_login(connection, "postgres", PASSWORD)
        with pytest.raises(ValueError, match="too short"):
            await enable_login(connection, "shaidago_public", "short")


async def test_mapping_options_let_the_restricted_role_insert_without_read_back(
    engines: dict[str, AsyncEngine],
) -> None:
    statements: list[str] = []
    public = engines["shaidago_public"]

    @event.listens_for(public.sync_engine, "before_cursor_execute")
    def capture(_c: object, _cur: object, statement: str, *_rest: object) -> None:
        statements.append(statement)

    async with AsyncSession(public, expire_on_commit=False) as session, session.begin():
        session.add(ReportRow(id=uuid.uuid4(), created_at=datetime.now(UTC), body="orm text"))
        await session.flush()
    inserts = [s for s in statements if s.lstrip().upper().startswith("INSERT")]
    assert inserts
    assert all("RETURNING" not in s.upper() for s in inserts)


async def test_default_mapping_fails_for_the_restricted_role_which_is_why_the_options_exist(
    engines: dict[str, AsyncEngine],
) -> None:
    async with AsyncSession(engines["shaidago_public"]) as session:
        session.add(NaiveReportRow(id=uuid.uuid4(), created_at=datetime.now(UTC), body="naive"))
        with pytest.raises((ProgrammingError, DBAPIError)) as raised:
            await session.flush()
    assert getattr(raised.value.orig, "sqlstate", None) == INSUFFICIENT_PRIVILEGE
