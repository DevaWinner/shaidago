import asyncio

import psycopg
import pytest
from sqlalchemy import text
from sqlalchemy.engine import URL
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from shaidago.shared.database import Database, build_engine
from shaidago.shared.problems import CONFLICT, ProblemError


@pytest.fixture
async def table(database: Database) -> str:
    async with database.unit_of_work() as session:
        await session.execute(text("DROP TABLE IF EXISTS kernel_probe"))
        await session.execute(text("CREATE TABLE kernel_probe (id int PRIMARY KEY, note text)"))
    return "kernel_probe"


async def insert(session: AsyncSession, table: str, row_id: int, note: str) -> None:
    await session.execute(
        text(f"INSERT INTO {table} VALUES (:id, :note)"),
        {"id": row_id, "note": note},
    )


async def count(database: Database, table: str) -> int:
    async with database.unit_of_work() as session:
        return (await session.execute(text(f"SELECT count(*) FROM {table}"))).scalar_one()


async def insert_then_fail(database: Database, table: str) -> None:
    async with database.unit_of_work() as session:
        await insert(session, table, 2, "b")
        raise RuntimeError("boom")


async def test_unit_of_work_commits_when_the_block_succeeds(database: Database, table: str) -> None:
    async with database.unit_of_work() as session:
        await insert(session, table, 1, "a")
    assert await count(database, table) == 1


async def test_unit_of_work_rolls_back_when_the_block_raises(
    database: Database, table: str
) -> None:
    with pytest.raises(RuntimeError, match="boom"):
        await insert_then_fail(database, table)
    assert await count(database, table) == 0


async def test_session_is_utc_and_has_a_statement_timeout(database: Database) -> None:
    async with database.unit_of_work() as session:
        assert (await session.execute(text("SHOW timezone"))).scalar_one() == "UTC"
        assert (await session.execute(text("SHOW statement_timeout"))).scalar_one() == "5s"
        name = (await session.execute(text("SHOW application_name"))).scalar_one()
        assert name == "shaidago-test"


async def test_a_slow_statement_is_cancelled_by_the_server(database_url: URL) -> None:
    engine = build_engine(database_url, application_name="t", statement_timeout_ms=200)
    try:
        with pytest.raises(DBAPIError) as raised:
            async with Database(engine).unit_of_work() as session:
                await session.execute(text("SELECT pg_sleep(3)"))
        assert getattr(raised.value.orig, "sqlstate", None) == "57014"  # query_canceled
    finally:
        await engine.dispose()


async def test_unique_violation_is_translated_to_a_conflict_problem(
    database: Database, table: str
) -> None:
    async with database.unit_of_work() as session:
        await insert(session, table, 5, "x")
    with pytest.raises(ProblemError) as raised:
        async with database.unit_of_work() as session:
            await insert(session, table, 5, "dup")
    assert raised.value.problem is CONFLICT
    assert "kernel_probe" not in str(raised.value)
    assert await count(database, table) == 1


async def test_a_conflict_raised_at_commit_time_is_translated_too(
    database: Database, table: str
) -> None:
    deferred_unique = (
        "ALTER TABLE kernel_probe ADD CONSTRAINT kernel_unique UNIQUE (note) "
        "DEFERRABLE INITIALLY DEFERRED"
    )
    async with database.unit_of_work() as session:
        await session.execute(text(deferred_unique))
        await insert(session, table, 7, "same")
    with pytest.raises(ProblemError) as raised:
        async with database.unit_of_work() as session:
            await insert(session, table, 8, "same")  # the violation only fires at commit
    assert raised.value.problem is CONFLICT


async def test_other_database_errors_are_not_translated(database: Database) -> None:
    with pytest.raises(DBAPIError):
        async with database.unit_of_work() as session:
            await session.execute(text("SELECT * FROM table_that_does_not_exist"))


async def test_pool_recovers_after_the_server_kills_a_pooled_connection(
    database: Database, engine: AsyncEngine
) -> None:
    async with database.unit_of_work() as session:
        await session.execute(text("SELECT 1"))
    async with engine.connect() as admin:
        await admin.execute(
            text(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE application_name = 'shaidago-test' AND pid <> pg_backend_pid()"
            )
        )
    await asyncio.sleep(0.1)
    async with database.unit_of_work() as session:  # pre-ping replaces the dead connection
        assert (await session.execute(text("SELECT 42"))).scalar_one() == 42


async def test_readiness_check_passes_and_fails_with_an_unreachable_server(
    database: Database, database_url: URL
) -> None:
    await database.check()
    dead = build_engine(
        database_url.set(port=1),
        application_name="t",
        statement_timeout_ms=1000,
        connect_timeout_seconds=1,
    )
    try:
        with pytest.raises(DBAPIError):
            await Database(dead).check()
    finally:
        await dead.dispose()


async def test_close_disposes_the_pool(
    engine: AsyncEngine,
    database_url: URL,
    admin_connection: psycopg.Connection[tuple[object, ...]],
) -> None:
    database = Database(engine)
    await database.open()
    await database.close()
    open_connections = admin_connection.execute(
        "SELECT count(*) FROM pg_stat_activity WHERE datname = %s AND application_name = %s",
        (database_url.database, "shaidago-test"),
    ).fetchone()
    assert open_connections == (0,)
