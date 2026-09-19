"""Async database kernel: engines, sessions, one unit of work per use case, error translation.

Routes never call ``commit()``. A use case opens ``Database.unit_of_work()``, which begins one
transaction, commits when the block succeeds, and rolls back when it raises. Known
concurrency and uniqueness outcomes become domain problems; every other database error stays
internal and surfaces as a generic 500 through the exception boundary.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Final

from sqlalchemy import text
from sqlalchemy.engine import URL
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from shaidago.shared.config import DatabaseSettings
from shaidago.shared.problems import CONFLICT, ProblemError

UNIQUE_VIOLATION: Final = "23505"
SERIALIZATION_FAILURE: Final = "40001"
DEADLOCK_DETECTED: Final = "40P01"
_CONFLICT_SQLSTATES: Final = frozenset({UNIQUE_VIOLATION, SERIALIZATION_FAILURE, DEADLOCK_DETECTED})


def sqlstate(error: BaseException) -> str | None:
    """The PostgreSQL SQLSTATE behind a SQLAlchemy error, if any."""
    original = getattr(error, "orig", None)
    code = getattr(original, "sqlstate", None)
    return code if isinstance(code, str) else None


def translate_database_error(error: DBAPIError) -> ProblemError | None:
    """Map only known, expected outcomes; anything else is returned as ``None`` (internal)."""
    if sqlstate(error) in _CONFLICT_SQLSTATES:
        return ProblemError(CONFLICT)
    return None


def build_engine(
    url: URL,
    *,
    application_name: str,
    statement_timeout_ms: int,
    connect_timeout_seconds: int = 5,
    pool_size: int = 5,
) -> AsyncEngine:
    """A pooled async engine with a UTC session, a statement timeout, and connection pre-ping."""
    return create_async_engine(
        url,
        pool_size=pool_size,
        pool_pre_ping=True,
        connect_args={
            "connect_timeout": connect_timeout_seconds,
            "application_name": application_name,
            "options": f"-c timezone=UTC -c statement_timeout={statement_timeout_ms}",
        },
    )


def create_engine(
    settings: DatabaseSettings, *, application_name: str, url: URL | None = None
) -> AsyncEngine:
    """Engine from settings; ``url`` selects a role (the owner URL is the default)."""
    return build_engine(
        url or settings.sqlalchemy_url(),
        application_name=application_name,
        statement_timeout_ms=settings.statement_timeout_ms,
        connect_timeout_seconds=settings.connect_timeout_seconds,
        pool_size=settings.pool_size,
    )


class Database:
    """One engine plus its session factory; also a managed resource and a readiness probe."""

    name = "database"
    required = True

    def __init__(self, engine: AsyncEngine) -> None:
        self.engine = engine
        # expire_on_commit=False: committed objects stay readable without an implicit reload.
        self._sessions = async_sessionmaker(engine, expire_on_commit=False)

    @asynccontextmanager
    async def unit_of_work(self) -> AsyncGenerator[AsyncSession]:
        # The try wraps the whole block so errors raised at commit time are translated too.
        try:
            async with self._sessions() as session, session.begin():
                yield session
        except DBAPIError as error:
            problem = translate_database_error(error)
            if problem is None:
                raise
            raise problem from error

    async def open(self) -> None:
        # Pools connect lazily. The API deliberately starts with the database down and reports
        # it through readiness instead of crash-looping.
        return

    async def close(self) -> None:
        await self.engine.dispose()

    async def check(self) -> None:
        async with self.engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
