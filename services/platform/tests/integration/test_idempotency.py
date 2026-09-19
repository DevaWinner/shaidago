import asyncio
import uuid
from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime, timedelta

import psycopg
import pytest
from alembic import command
from sqlalchemy import text
from sqlalchemy.engine import URL
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from shaidago.db.provision import PASSWORD_VARIABLES, provision
from shaidago.db.revision import alembic_config
from shaidago.shared.clock import ManualClock
from shaidago.shared.database import Database, build_engine
from shaidago.shared.idempotency import (
    RETENTION,
    SEALED_WINDOW,
    Claimed,
    IdempotencyStore,
    Replay,
    fingerprint,
    purge_expired,
)
from shaidago.shared.ids import Uuid7Generator
from shaidago.shared.problems import ALREADY_RECEIVED, IDEMPOTENCY_CONFLICT, ProblemError
from tests.integration.conftest import disposable_database

PEPPER = b"p" * 32
KEY = "3f2b8c1e-9d4a-4b6e-8a1c-2d5e7f9a0b3c"
OPERATION = "reports.submit"
CODE = b"SG-7GQ2K-9M4XV-C8HTB-3WNZD-R"
PASSWORD = "idempotency-test-password-"
START = datetime(2026, 9, 19, 12, 0, tzinfo=UTC)


@pytest.fixture(scope="module")
def urls(admin_connection: psycopg.Connection[tuple[object, ...]]) -> Iterator[dict[str, URL]]:
    with disposable_database(admin_connection) as owner:
        command.upgrade(alembic_config(owner.render_as_string(hide_password=False)), "head")
        provision(
            {"DATABASE_URL": owner.render_as_string(hide_password=False)}
            | {variable: PASSWORD + role for role, variable in PASSWORD_VARIABLES.items()}
        )
        yield {
            role: owner.set(username=role, password=PASSWORD + role) for role in PASSWORD_VARIABLES
        } | {"owner": owner}


@pytest.fixture
async def public(urls: dict[str, URL]) -> AsyncIterator[Database]:
    engine = build_engine(
        urls["shaidago_public"], application_name="idem", statement_timeout_ms=8000
    )
    yield Database(engine)
    await engine.dispose()


@pytest.fixture
async def owner_engine(urls: dict[str, URL]) -> AsyncIterator[AsyncEngine]:
    engine = build_engine(urls["owner"], application_name="owner", statement_timeout_ms=8000)
    yield engine
    await engine.dispose()


@pytest.fixture
def clock() -> ManualClock:
    return ManualClock(START)


def store(session: AsyncSession, clock: ManualClock) -> IdempotencyStore:
    return IdempotencyStore(session, pepper=PEPPER, clock=clock, ids=Uuid7Generator(clock))


def unique_key() -> str:
    return str(uuid.uuid4())


async def submit(
    database: Database, clock: ManualClock, key: str, fp: bytes, code: bytes = CODE
) -> Claimed | Replay:
    """One use case: claim, do work, seal the result, all in one transaction."""
    async with database.unit_of_work() as session:
        idem = store(session, clock)
        outcome = await idem.begin(OPERATION, key, fp)
        if isinstance(outcome, Replay):
            return outcome
        await idem.complete(OPERATION, key, status=201, payload=code)
        return Claimed()


async def test_first_call_claims_and_a_retry_replays_the_same_result(
    public: Database, clock: ManualClock
) -> None:
    key, fp = unique_key(), fingerprint("POST", "project-1", "body")
    assert await submit(public, clock, key, fp) == Claimed()
    assert await submit(public, clock, key, fp, code=b"a different code") == Replay(201, CODE)


async def test_same_key_with_a_different_request_is_a_conflict(
    public: Database, clock: ManualClock
) -> None:
    key = unique_key()
    await submit(public, clock, key, fingerprint("a"))
    with pytest.raises(ProblemError) as raised:
        await submit(public, clock, key, fingerprint("b"))
    assert raised.value.problem is IDEMPOTENCY_CONFLICT


async def test_the_replay_window_ends_then_retention_ends(
    public: Database, clock: ManualClock
) -> None:
    key, fp = unique_key(), fingerprint("x")
    await submit(public, clock, key, fp)
    clock.advance(SEALED_WINDOW - timedelta(seconds=1))
    assert isinstance(await submit(public, clock, key, fp), Replay)
    clock.advance(timedelta(seconds=2))
    with pytest.raises(ProblemError) as raised:
        await submit(public, clock, key, fp)
    assert raised.value.problem is ALREADY_RECEIVED
    clock.advance(RETENTION)
    assert await submit(public, clock, key, fp) == Claimed()


async def test_a_failed_use_case_leaves_no_claim_so_the_retry_can_proceed(
    public: Database, clock: ManualClock
) -> None:
    key, fp = unique_key(), fingerprint("y")

    async def failing() -> None:
        async with public.unit_of_work() as session:
            await store(session, clock).begin(OPERATION, key, fp)
            raise RuntimeError("work failed after claiming")

    with pytest.raises(RuntimeError, match="work failed"):
        await failing()
    assert await submit(public, clock, key, fp) == Claimed()


async def test_concurrent_duplicates_serialise_and_the_second_replays_the_first(
    public: Database, clock: ManualClock
) -> None:
    key, fp = unique_key(), fingerprint("race")
    first_claimed, release_first = asyncio.Event(), asyncio.Event()

    async def first() -> Claimed | Replay:
        async with public.unit_of_work() as session:
            idem = store(session, clock)
            outcome = await idem.begin(OPERATION, key, fp)
            first_claimed.set()
            await release_first.wait()
            await idem.complete(OPERATION, key, status=201, payload=CODE)
            return outcome

    first_task = asyncio.create_task(first())
    await first_claimed.wait()
    second_task = asyncio.create_task(submit(public, clock, key, fp, code=b"second"))
    done, _pending = await asyncio.wait({second_task}, timeout=0.5)
    assert not done, "the duplicate must wait for the first transaction"
    release_first.set()
    assert await first_task == Claimed()
    assert await second_task == Replay(201, CODE)


async def test_public_role_has_no_privilege_on_the_table_only_on_the_functions(
    public: Database,
) -> None:
    for statement in (
        "SELECT * FROM app.idempotency_records",
        "INSERT INTO app.idempotency_records (id) VALUES (gen_random_uuid())",
        "UPDATE app.idempotency_records SET state = 'completed'",
        "DELETE FROM app.idempotency_records",
        "SELECT app.idempotency_purge(now(), 10)",
    ):
        with pytest.raises(DBAPIError) as raised:
            async with public.unit_of_work() as session:
                await session.execute(text(statement))
        assert getattr(raised.value.orig, "sqlstate", None) == "42501", statement


async def test_stored_rows_contain_no_key_and_no_plaintext_result(
    public: Database, owner_engine: AsyncEngine, clock: ManualClock
) -> None:
    key = unique_key()
    await submit(public, clock, key, fingerprint("leak-check"))
    async with owner_engine.connect() as connection:
        rows = (
            await connection.execute(
                text(
                    "SELECT operation, key_hash, fingerprint, sealed_response "
                    "FROM app.idempotency_records"
                )
            )
        ).all()
    blob = b"".join(bytes(v) if not isinstance(v, str) else v.encode() for row in rows for v in row)
    assert key.encode() not in blob
    assert CODE not in blob


async def test_worker_purge_scrubs_sealed_results_and_deletes_expired_records(
    public: Database, urls: dict[str, URL], owner_engine: AsyncEngine, clock: ManualClock
) -> None:
    key = unique_key()
    await submit(public, clock, key, fingerprint("purge-me"))
    worker_engine = build_engine(
        urls["shaidago_worker"], application_name="w", statement_timeout_ms=8000
    )
    worker = Database(worker_engine)
    try:
        clock.advance(SEALED_WINDOW + timedelta(seconds=1))
        async with worker.unit_of_work() as session:
            assert await purge_expired(session, clock) >= 1
        async with owner_engine.connect() as connection:
            scrubbed = (
                await connection.execute(
                    text(
                        "SELECT count(*) FROM app.idempotency_records "
                        "WHERE sealed_response IS NOT NULL AND sealed_until <= :now"
                    ),
                    {"now": clock.now()},
                )
            ).scalar_one()
        assert scrubbed == 0
        clock.advance(RETENTION)
        async with worker.unit_of_work() as session:
            await purge_expired(session, clock)
        async with owner_engine.connect() as connection:
            remaining = (
                await connection.execute(
                    text("SELECT count(*) FROM app.idempotency_records WHERE expires_at <= :now"),
                    {"now": clock.now()},
                )
            ).scalar_one()
        assert remaining == 0
    finally:
        await worker_engine.dispose()


async def test_completing_an_unclaimed_key_fails_loudly(
    public: Database, clock: ManualClock
) -> None:
    with pytest.raises(DBAPIError) as raised:
        async with public.unit_of_work() as session:
            await store(session, clock).complete(OPERATION, unique_key(), status=201, payload=b"x")
    assert getattr(raised.value.orig, "sqlstate", None) == "P0002"
