"""Session issue, validity, expiry, revocation, and the operations that revoke them."""

import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.engine import URL
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from shaidago.auth.passwords import PasswordPolicy, PasswordVerifier
from shaidago.auth.reviewers import ReviewerRecord, ReviewerService, find_reviewer
from shaidago.auth.sessions import SessionLifetimes, SessionService
from shaidago.shared.clock import ManualClock
from shaidago.shared.database import Database, build_engine
from shaidago.shared.ids import Uuid7Generator
from tests.integration.support import Plain

KEY = b"s" * 32
START = datetime(2026, 9, 19, 12, 0, tzinfo=UTC)
IDLE = timedelta(minutes=30)
ABSOLUTE = timedelta(hours=8)
FAST = PasswordVerifier(PasswordPolicy(time_cost=1, memory_cost_kib=1024, parallelism=1))
PASSWORD = "a-long-enough-reviewer-password"
PRIVILEGE = "42501"


@pytest.fixture
async def owner_db(role_urls: dict[str, URL]) -> AsyncIterator[Database]:
    engine = build_engine(role_urls["owner"], application_name="owner", statement_timeout_ms=8000)
    yield Database(engine)
    await engine.dispose()


@pytest.fixture
def clock() -> ManualClock:
    return ManualClock(START)


def sessions(session: AsyncSession, clock: ManualClock) -> SessionService:
    return SessionService(
        session,
        key=KEY,
        clock=clock,
        ids=Uuid7Generator(clock),
        lifetimes=SessionLifetimes(IDLE, ABSOLUTE),
    )


def reviewers(session: AsyncSession, clock: ManualClock) -> ReviewerService:
    return ReviewerService(
        session, clock=clock, ids=Uuid7Generator(clock), passwords=FAST, deployed=False
    )


async def new_reviewer(db: Database, clock: ManualClock, role: str = "reviewer") -> ReviewerRecord:
    identifier = f"sess-{uuid.uuid4().hex[:10]}"
    async with db.unit_of_work() as session:
        await reviewers(session, clock).create(identifier, PASSWORD, role)  # type: ignore[arg-type]
    async with db.unit_of_work() as session:
        found = await find_reviewer(session, identifier)
    assert found is not None
    return found


async def resolve(db: Database, clock: ManualClock, token: str | None):
    async with db.unit_of_work() as session:
        return await sessions(session, clock).resolve(token)


async def test_an_issued_session_resolves_to_its_reviewer_and_carries_256_bits(
    owner_db: Database, clock: ManualClock
) -> None:
    reviewer = await new_reviewer(owner_db, clock, "admin")
    async with owner_db.unit_of_work() as session:
        issued = await sessions(session, clock).issue(reviewer)
    assert len(issued.token) >= 43  # 32 random bytes, URL-safe base64
    assert issued.absolute_expires_at == START + ABSOLUTE
    principal = await resolve(owner_db, clock, issued.token)
    assert principal is not None
    assert (principal.reviewer_id, principal.role, principal.session_id) == (
        reviewer.id,
        "admin",
        issued.session_id,
    )
    assert issued.token not in repr(issued)


async def test_tokens_are_unique_and_never_stored_in_any_readable_form(
    owner_db: Database, clock: ManualClock
) -> None:
    reviewer = await new_reviewer(owner_db, clock)
    async with owner_db.unit_of_work() as session:
        issued = [await sessions(session, clock).issue(reviewer) for _ in range(20)]
    assert len({i.token for i in issued}) == 20
    async with owner_db.unit_of_work() as session:
        rows = (await session.execute(text("SELECT * FROM app.reviewer_sessions"))).all()
    stored = b"".join(_as_bytes(value) for row in rows for value in row)
    for one in issued:
        assert one.token.encode() not in stored
        assert one.csrf_token.encode() not in stored
    audit = (await _all_text(owner_db, "SELECT details::text FROM app.audit_events")).encode()
    assert all(one.token.encode() not in audit for one in issued)


def _as_bytes(value: object) -> bytes:
    if isinstance(value, bytes):
        return value
    if isinstance(value, memoryview):
        return value.tobytes()
    return str(value).encode()


async def _all_text(db: Database, sql: str) -> str:
    async with db.unit_of_work() as session:
        return " ".join(str(r[0]) for r in await session.execute(text(sql)))


async def test_unknown_malformed_and_empty_tokens_resolve_to_nothing(
    owner_db: Database, clock: ManualClock
) -> None:
    for token in (None, "", "x" * 43, "x" * 129, "é" * 10, "' OR 1=1 --"):
        assert await resolve(owner_db, clock, token) is None


async def test_idle_and_absolute_expiry_use_the_injected_clock(
    owner_db: Database, clock: ManualClock
) -> None:
    reviewer = await new_reviewer(owner_db, clock)
    async with owner_db.unit_of_work() as session:
        issued = await sessions(session, clock).issue(reviewer)
    clock.advance(IDLE - timedelta(seconds=1))
    assert await resolve(owner_db, clock, issued.token) is not None  # refreshes last use
    clock.advance(IDLE - timedelta(seconds=1))
    assert await resolve(owner_db, clock, issued.token) is not None, "activity extends the session"
    clock.advance(IDLE + timedelta(seconds=1))
    assert await resolve(owner_db, clock, issued.token) is None, "idle expiry"
    async with owner_db.unit_of_work() as session:
        fresh = await sessions(session, clock).issue(reviewer)
    for _ in range(19):  # steady activity every 25 minutes for 7 hours 55 minutes
        clock.advance(timedelta(minutes=25))
        assert await resolve(owner_db, clock, fresh.token) is not None
    clock.advance(timedelta(minutes=25))  # 8 hours 20 minutes after issue
    assert await resolve(owner_db, clock, fresh.token) is None, "absolute expiry despite activity"


async def test_last_use_is_written_at_most_once_a_minute(
    owner_db: Database, clock: ManualClock
) -> None:
    reviewer = await new_reviewer(owner_db, clock)
    async with owner_db.unit_of_work() as session:
        issued = await sessions(session, clock).issue(reviewer)

    async def last_used() -> datetime:
        async with owner_db.unit_of_work() as session:
            return (
                await session.execute(
                    text("SELECT last_used_at FROM app.reviewer_sessions WHERE id = :i"),
                    {"i": issued.session_id},
                )
            ).scalar_one()

    clock.advance(timedelta(seconds=30))
    await resolve(owner_db, clock, issued.token)
    assert await last_used() == START
    clock.advance(timedelta(seconds=31))
    await resolve(owner_db, clock, issued.token)
    assert await last_used() == clock.now()


async def test_logout_revokes_only_that_session_and_replay_fails(
    owner_db: Database, clock: ManualClock
) -> None:
    reviewer = await new_reviewer(owner_db, clock)
    async with owner_db.unit_of_work() as session:
        service = sessions(session, clock)
        first, second = await service.issue(reviewer), await service.issue(reviewer)
    async with owner_db.unit_of_work() as session:
        await sessions(session, clock).revoke_token(first.token)
    assert await resolve(owner_db, clock, first.token) is None, "replay after logout"
    assert await resolve(owner_db, clock, second.token) is not None
    async with owner_db.unit_of_work() as session:
        await sessions(session, clock).revoke_token(first.token)  # repeat is harmless


async def test_disabling_a_reviewer_revokes_every_session_atomically(
    owner_db: Database, clock: ManualClock
) -> None:
    reviewer = await new_reviewer(owner_db, clock)
    other = await new_reviewer(owner_db, clock)
    async with owner_db.unit_of_work() as session:
        service = sessions(session, clock)
        mine = [await service.issue(reviewer) for _ in range(3)]
        theirs = await service.issue(other)
    async with owner_db.unit_of_work() as session:
        await reviewers(session, clock).disable(reviewer.id)
    for issued in mine:
        assert await resolve(owner_db, clock, issued.token) is None
    assert await resolve(owner_db, clock, theirs.token) is not None
    reasons = await _all_text(
        owner_db,
        f"SELECT DISTINCT revocation_reason FROM app.reviewer_sessions WHERE reviewer_id = '{reviewer.id}'",
    )
    assert reasons == "disabled"

    async def failing_disable() -> None:
        async with owner_db.unit_of_work() as session:
            await reviewers(session, clock).disable(other.id)
            raise RuntimeError("abort after disabling")

    with pytest.raises(RuntimeError):
        await failing_disable()
    assert await resolve(owner_db, clock, theirs.token) is not None, "rollback keeps the session"


async def test_a_password_change_ends_all_sessions_and_the_old_one_never_returns(
    owner_db: Database, clock: ManualClock
) -> None:
    reviewer = await new_reviewer(owner_db, clock)
    async with owner_db.unit_of_work() as session:
        issued = await sessions(session, clock).issue(reviewer)
    async with owner_db.unit_of_work() as session:
        await reviewers(session, clock).change_password(reviewer.id, "another-long-password-1")
    assert await resolve(owner_db, clock, issued.token) is None
    async with owner_db.unit_of_work() as session:
        updated = await find_reviewer(session, reviewer.identifier)
    assert updated is not None
    assert updated.credential_version == reviewer.credential_version + 1
    async with owner_db.unit_of_work() as session:
        fresh = await sessions(session, clock).issue(updated)
    assert await resolve(owner_db, clock, fresh.token) is not None


async def test_a_role_downgrade_takes_effect_immediately_even_without_revocation_rows(
    owner_db: Database, clock: ManualClock
) -> None:
    reviewer = await new_reviewer(owner_db, clock, "admin")
    async with owner_db.unit_of_work() as session:
        issued = await sessions(session, clock).issue(reviewer)
        # A raw role change that forgets to revoke must still not leave a stale privilege.
        await session.execute(
            text("UPDATE app.reviewers SET role = 'reviewer' WHERE id = :i"), {"i": reviewer.id}
        )
    assert await resolve(owner_db, clock, issued.token) is None
    async with owner_db.unit_of_work() as session:
        await reviewers(session, clock).set_role(reviewer.id, "admin")
        again = await find_reviewer(session, reviewer.identifier)
    assert again is not None
    async with owner_db.unit_of_work() as session:
        after = await sessions(session, clock).issue(again)
    assert (await resolve(owner_db, clock, after.token)) is not None


async def sqlstate_of(action: Callable[[], Awaitable[object]]) -> str | None:
    with pytest.raises(DBAPIError) as raised:
        await action()
    return getattr(raised.value.orig, "sqlstate", None)


async def test_only_the_reviewer_role_touches_sessions_and_only_permitted_columns(
    role_urls: dict[str, URL], owner_db: Database, clock: ManualClock
) -> None:
    reviewer = await new_reviewer(owner_db, clock)
    async with owner_db.unit_of_work() as session:
        issued = await sessions(session, clock).issue(reviewer)
    engines = {
        role: build_engine(role_urls[role], application_name=role, statement_timeout_ms=8000)
        for role in ("shaidago_public", "shaidago_worker", "shaidago_reviewer")
    }
    try:
        for role in ("shaidago_public", "shaidago_worker"):
            db = Plain(engines[role])

            async def read(db: Plain = db) -> None:
                async with db.unit_of_work() as session:
                    await session.execute(text("SELECT * FROM app.reviewer_sessions"))

            assert await sqlstate_of(read) == PRIVILEGE
        reviewer_db = Plain(engines["shaidago_reviewer"])
        async with reviewer_db.unit_of_work() as session:
            await session.execute(
                text("UPDATE app.reviewer_sessions SET last_used_at = now() WHERE id = :i"),
                {"i": issued.session_id},
            )

        def attempt(sql: str) -> Callable[[], Awaitable[None]]:
            async def run() -> None:
                async with reviewer_db.unit_of_work() as session:
                    await session.execute(text(sql), {"i": issued.session_id})

            return run

        for sql in (
            "UPDATE app.reviewer_sessions SET reviewer_id = gen_random_uuid() WHERE id = :i",
            "UPDATE app.reviewer_sessions SET absolute_expires_at = now() + interval '30 days' WHERE id = :i",
            "UPDATE app.reviewer_sessions SET token_hmac = '\\x00' WHERE id = :i",
            "DELETE FROM app.reviewer_sessions WHERE id = :i",
        ):
            assert await sqlstate_of(attempt(sql)) == PRIVILEGE, sql
    finally:
        for engine in engines.values():
            await engine.dispose()
