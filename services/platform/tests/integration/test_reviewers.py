"""Reviewer users, the append-only audit log, and the bootstrap command."""

import json
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import UTC, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.engine import URL
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from shaidago.audit.events import AuditWriter
from shaidago.auth.bootstrap import BootstrapError, bootstrap
from shaidago.auth.passwords import PasswordPolicy, PasswordVerifier, WeakPasswordError
from shaidago.auth.reviewers import IdentifierError, ReviewerService, find_reviewer
from shaidago.shared.clock import ManualClock
from shaidago.shared.database import Database, build_engine
from shaidago.shared.ids import Uuid7Generator
from shaidago.shared.problems import CONFLICT, ProblemError
from tests.integration.support import Plain

CHECK_VIOLATION = "23514"
IMMUTABLE = "55000"
PRIVILEGE = "42501"
FAST = PasswordVerifier(PasswordPolicy(time_cost=1, memory_cost_kib=1024, parallelism=1))
PASSWORD = "a-long-enough-reviewer-password"
START = datetime(2026, 9, 19, 12, 0, tzinfo=UTC)


@pytest.fixture
async def owner_db(role_urls: dict[str, URL]) -> AsyncIterator[Database]:
    engine = build_engine(role_urls["owner"], application_name="owner", statement_timeout_ms=8000)
    yield Database(engine)
    await engine.dispose()


@pytest.fixture
async def role_db(
    role_urls: dict[str, URL], request: pytest.FixtureRequest
) -> AsyncIterator[Plain]:
    engine = build_engine(role_urls[request.param], application_name="r", statement_timeout_ms=8000)
    yield Plain(engine)
    await engine.dispose()


async def sqlstate_of(action: Callable[[], Awaitable[object]]) -> str | None:
    with pytest.raises(DBAPIError) as raised:
        await action()
    return getattr(raised.value.orig, "sqlstate", None)


def service(session: AsyncSession, deployed: bool = False) -> ReviewerService:
    clock = ManualClock(START)
    return ReviewerService(
        session, clock=clock, ids=Uuid7Generator(clock), passwords=FAST, deployed=deployed
    )


def unique(prefix: str = "rev") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


async def test_a_reviewer_is_created_with_a_normalised_identifier_and_an_argon2id_hash(
    owner_db: Database,
) -> None:
    identifier = unique("Mixed-Case")
    async with owner_db.unit_of_work() as session:
        reviewer_id = await service(session).create(
            f"  {identifier.upper()} ", PASSWORD, "reviewer"
        )
    async with owner_db.unit_of_work() as session:
        found = await find_reviewer(session, identifier.upper())
    assert found is not None
    assert (found.id, found.identifier, found.role, found.state) == (
        reviewer_id,
        identifier.lower(),
        "reviewer",
        "active",
    )
    assert found.credential_version == 1
    assert found.password_hash.startswith("$argon2id$")
    assert PASSWORD not in found.password_hash


async def test_duplicate_identifiers_conflict_regardless_of_case(owner_db: Database) -> None:
    identifier = unique()
    async with owner_db.unit_of_work() as session:
        await service(session).create(identifier, PASSWORD, "admin")
    with pytest.raises(ProblemError) as raised:
        async with owner_db.unit_of_work() as session:
            await service(session).create(identifier.upper(), PASSWORD, "reviewer")
    assert raised.value.problem is CONFLICT


async def test_weak_passwords_and_bad_identifiers_create_nothing(owner_db: Database) -> None:
    identifier = unique()
    for bad_password, deployed in (("short", False), ("change-me-reviewer-bootstrap", True)):
        with pytest.raises(WeakPasswordError):
            async with owner_db.unit_of_work() as session:
                await service(session, deployed).create(identifier, bad_password, "reviewer")
    with pytest.raises(IdentifierError):
        async with owner_db.unit_of_work() as session:
            await service(session).create("no", PASSWORD, "reviewer")
    async with owner_db.unit_of_work() as session:
        assert await find_reviewer(session, identifier) is None


async def test_database_rejects_bad_roles_states_identifiers_and_non_argon_hashes(
    owner_db: Database,
) -> None:
    async def insert(**overrides: str) -> None:
        fields = {
            "identifier": unique(),
            "hash": "$argon2id$x",
            "role": "reviewer",
            "state": "active",
        } | overrides
        async with owner_db.unit_of_work() as session:
            await session.execute(
                text(
                    "INSERT INTO app.reviewers VALUES (gen_random_uuid(), :identifier, :hash, :role, "
                    ":state, 1, now(), now(), NULL)"
                ),
                fields,
            )

    for bad in (
        {"role": "superuser"},
        {"state": "locked"},
        {"identifier": "UPPER-case"},
        {"identifier": "x"},
        {"hash": "plaintext-password"},
        {"hash": "$argon2i$v=19$..."},
    ):
        with pytest.raises(DBAPIError) as raised:
            await insert(**bad)
        assert getattr(raised.value.orig, "sqlstate", None) == CHECK_VIOLATION, bad


async def test_creating_a_reviewer_writes_an_audit_event_without_secrets(
    owner_db: Database,
) -> None:
    identifier = unique()
    async with owner_db.unit_of_work() as session:
        reviewer_id = await service(session).create(
            identifier, PASSWORD, "admin", request_id="req-1"
        )
    async with owner_db.unit_of_work() as session:
        row = (
            await session.execute(
                text(
                    "SELECT actor_type, event, subject_type, outcome, request_id, details "
                    "FROM app.audit_events WHERE subject_id = :id"
                ),
                {"id": reviewer_id},
            )
        ).one()
    assert (row.actor_type, row.event, row.subject_type, row.outcome, row.request_id) == (
        "system", "reviewer_created", "reviewer", "success", "req-1",
    )  # fmt: skip
    dump = json.dumps(row.details)
    assert row.details == {"role": "admin"}
    assert PASSWORD not in dump
    assert identifier not in dump


async def test_the_audit_writer_redacts_sensitive_details_before_storing(
    owner_db: Database,
) -> None:
    clock = ManualClock(START)
    async with owner_db.unit_of_work() as session:
        event_id = await AuditWriter(session, clock, Uuid7Generator(clock)).record(
            "probe_event",
            actor_type="system",
            details={"password": "hunter2-canary", "note": "ip 203.0.113.9 seen", "count": 3},
        )
    async with owner_db.unit_of_work() as session:
        details = (
            await session.execute(
                text("SELECT details FROM app.audit_events WHERE id = :id"), {"id": event_id}
            )
        ).scalar_one()
    assert "hunter2-canary" not in json.dumps(details)
    assert "203.0.113.9" not in json.dumps(details)
    assert details["count"] == 3


async def test_audit_events_can_never_be_changed_deleted_or_truncated_even_by_the_owner(
    owner_db: Database,
) -> None:
    clock = ManualClock(START)
    async with owner_db.unit_of_work() as session:
        event_id = await AuditWriter(session, clock, Uuid7Generator(clock)).record(
            "immutable_probe", actor_type="system"
        )

    def statement(sql: str) -> Callable[[], Awaitable[None]]:
        async def run() -> None:
            async with owner_db.unit_of_work() as session:
                await session.execute(text(sql), {"id": event_id})

        return run

    for sql in (
        "UPDATE app.audit_events SET outcome = 'failure' WHERE id = :id",
        "DELETE FROM app.audit_events WHERE id = :id",
        "TRUNCATE app.audit_events",
    ):
        assert await sqlstate_of(statement(sql)) == IMMUTABLE, sql


@pytest.mark.parametrize(
    "role_db", ["shaidago_public", "shaidago_worker", "shaidago_readonly_ops"], indirect=True
)
async def test_other_roles_cannot_read_or_write_reviewers(role_db: Plain) -> None:
    async def read() -> None:
        async with role_db.unit_of_work() as session:
            await session.execute(text("SELECT * FROM app.reviewers"))

    assert await sqlstate_of(read) == PRIVILEGE


@pytest.mark.parametrize("role_db", ["shaidago_reviewer"], indirect=True)
async def test_the_reviewer_role_can_read_and_update_permitted_columns_but_not_create_or_delete(
    role_db: Plain, owner_db: Database
) -> None:
    identifier = unique()
    async with owner_db.unit_of_work() as session:
        await service(session).create(identifier, PASSWORD, "reviewer")
    async with role_db.unit_of_work() as session:
        assert (await session.execute(text("SELECT count(*) FROM app.reviewers"))).scalar_one() >= 1
        await session.execute(
            text("UPDATE app.reviewers SET last_sign_in_at = now() WHERE identifier = :i"),
            {"i": identifier},
        )

    def statement(sql: str) -> Callable[[], Awaitable[None]]:
        async def run() -> None:
            async with role_db.unit_of_work() as session:
                await session.execute(text(sql), {"i": identifier})

        return run

    for sql in (
        "UPDATE app.reviewers SET role = 'admin' WHERE identifier = :i",
        "UPDATE app.reviewers SET identifier = 'renamed-user' WHERE identifier = :i",
        "DELETE FROM app.reviewers WHERE identifier = :i",
        "INSERT INTO app.reviewers VALUES (gen_random_uuid(), 'new-user', '$argon2id$x', 'admin', 'active', 1, now(), now(), NULL)",
    ):
        assert await sqlstate_of(statement(sql)) == PRIVILEGE, sql


def environment(role_urls: dict[str, URL], **overrides: str) -> dict[str, str]:
    base = {
        "DATABASE_URL": role_urls["owner"].render_as_string(hide_password=False),
        "REVIEWER_BOOTSTRAP_IDENTIFIER": unique("boot"),
        "REVIEWER_BOOTSTRAP_PASSWORD": "a-strong-bootstrap-password",
    }
    return base | overrides


async def test_bootstrap_creates_once_and_never_overwrites(
    role_urls: dict[str, URL], owner_db: Database
) -> None:
    env = environment(role_urls, REVIEWER_BOOTSTRAP_ROLE="admin")
    assert await bootstrap(env) == "created"
    async with owner_db.unit_of_work() as session:
        before = await find_reviewer(session, env["REVIEWER_BOOTSTRAP_IDENTIFIER"])
    assert before is not None
    assert before.role == "admin"
    assert (
        await bootstrap(env | {"REVIEWER_BOOTSTRAP_PASSWORD": "a-different-strong-password"})
        == "exists"
    )
    async with owner_db.unit_of_work() as session:
        after = await find_reviewer(session, env["REVIEWER_BOOTSTRAP_IDENTIFIER"])
    assert after is not None
    assert after.password_hash == before.password_hash


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"REVIEWER_BOOTSTRAP_PASSWORD": ""}, "REVIEWER_BOOTSTRAP_PASSWORD is not set"),
        ({"REVIEWER_BOOTSTRAP_IDENTIFIER": ""}, "REVIEWER_BOOTSTRAP_IDENTIFIER is not set"),
        ({"REVIEWER_BOOTSTRAP_ROLE": "root"}, "must be reviewer or admin"),
        ({"REVIEWER_BOOTSTRAP_PASSWORD": "short"}, "REVIEWER_BOOTSTRAP_PASSWORD: password must be"),
        (
            {"REVIEWER_BOOTSTRAP_IDENTIFIER": "no"},
            "REVIEWER_BOOTSTRAP_IDENTIFIER is not acceptable",
        ),
        (
            {
                "APP_ENV": "production",
                "REVIEWER_BOOTSTRAP_PASSWORD": "change-me-reviewer-bootstrap",
            },
            "placeholder or demo password is refused",
        ),
        ({"DATABASE_URL": "not a url"}, "DATABASE_URL is not a valid database URL"),
    ],
)
async def test_bootstrap_refuses_unusable_input_without_echoing_secrets(
    role_urls: dict[str, URL], override: dict[str, str], message: str
) -> None:
    env = environment(role_urls, **override)
    with pytest.raises(BootstrapError, match=message) as raised:
        await bootstrap(env)
    assert env["REVIEWER_BOOTSTRAP_PASSWORD"] == "" or env[
        "REVIEWER_BOOTSTRAP_PASSWORD"
    ] not in str(raised.value)
