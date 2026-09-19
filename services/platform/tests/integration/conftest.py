"""Integration fixtures against the Compose PostgreSQL (``make infra-up-core``).

Each session creates a disposable database and drops it afterwards, so committed-transaction
behaviour is real and nothing persists. Missing infrastructure fails loudly rather than skipping.
"""

import os
import uuid
from collections.abc import AsyncIterator, Generator, Iterator
from contextlib import contextmanager

import psycopg
import pytest
from alembic import command
from psycopg import sql
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import AsyncEngine

from shaidago.db.provision import PASSWORD_VARIABLES, provision
from shaidago.db.revision import alembic_config
from shaidago.shared.database import Database, build_engine
from tests.integration.public_catalogue import client, seed


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        if "tests/integration/" in item.nodeid:
            item.add_marker(pytest.mark.integration)


def _admin_connection_kwargs() -> dict[str, object]:
    return {
        "host": os.environ.get("INFRA_DB_HOST", "127.0.0.1"),
        "port": int(os.environ.get("INFRA_POSTGRES_PORT", "55432")),
        "user": os.environ.get("POSTGRES_USER", "shaidago"),
        "password": os.environ.get("POSTGRES_PASSWORD", ""),
        "dbname": "postgres",
        "autocommit": True,
        "connect_timeout": 5,
    }


@pytest.fixture(scope="session")
def admin_connection() -> Iterator[psycopg.Connection[tuple[object, ...]]]:
    try:
        connection = psycopg.connect(**_admin_connection_kwargs())  # pyright: ignore[reportArgumentType]
    except psycopg.OperationalError as error:
        pytest.fail(
            "PostgreSQL is not reachable. Run `make infra-up-core` and pass the environment "
            f"(`make backend-integration` does): {type(error).__name__}",
            pytrace=False,
        )
    with connection:
        yield connection


@contextmanager
def disposable_database(
    admin: psycopg.Connection[tuple[object, ...]],
) -> Generator[URL]:
    """Create an empty database, yield a URL to it as the bootstrap user, and drop it."""
    name = f"shaidago_test_{uuid.uuid4().hex[:12]}"
    admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    kwargs = _admin_connection_kwargs()
    try:
        yield URL.create(
            "postgresql+psycopg",
            username=str(kwargs["user"]),
            password=str(kwargs["password"]),
            host=str(kwargs["host"]),
            port=int(str(kwargs["port"])),
            database=name,
        )
    finally:
        admin.execute(
            sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(name))
        )


@pytest.fixture(scope="session")
def database_url(admin_connection: psycopg.Connection[tuple[object, ...]]) -> Iterator[URL]:
    with disposable_database(admin_connection) as url:
        yield url


@pytest.fixture
async def engine(database_url: URL) -> AsyncIterator[AsyncEngine]:
    engine = build_engine(database_url, application_name="shaidago-test", statement_timeout_ms=5000)
    yield engine
    await engine.dispose()


@pytest.fixture
async def database(engine: AsyncEngine) -> Database:
    return Database(engine)


@pytest.fixture(scope="module")
def role_urls(
    admin_connection: psycopg.Connection[tuple[object, ...]],
) -> Iterator[dict[str, URL]]:
    """A migrated database with every application role able to log in, keyed by role name."""
    password = "module-role-password-"
    with disposable_database(admin_connection) as owner:
        command.upgrade(alembic_config(owner.render_as_string(hide_password=False)), "head")
        provision(
            {"DATABASE_URL": owner.render_as_string(hide_password=False)}
            | {variable: password + role for role, variable in PASSWORD_VARIABLES.items()}
        )
        yield {
            role: owner.set(username=role, password=password + role) for role in PASSWORD_VARIABLES
        } | {"owner": owner}


# Re-exported so pytest registers the shared catalogue fixture for every integration module.
__all__ = ["client", "seed"]
