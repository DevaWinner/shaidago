"""Alembic environment. Uses a plain sync engine; it never imports the FastAPI application."""

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool
from sqlalchemy.engine import Connection, make_url

from shaidago.db.metadata import include_object
from shaidago.db.registry import metadata

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

# `registry` imports every table module so its tables register on `metadata`.
target_metadata = metadata

MANAGED_SCHEMAS = frozenset({"app", "public_api"})


def _url() -> str:
    override = config.attributes.get("url")
    if override is not None:
        return str(override)
    # The migration job needs the owner URL and nothing else: none of the application roles'
    # URLs, keys, or provider credentials is required (or wanted) in its environment.
    raw = os.environ.get("DATABASE_URL", "")
    parsed = make_url(raw) if raw else None
    if (
        parsed is None
        or parsed.drivername != "postgresql+psycopg"
        or not parsed.host
        or not parsed.database
    ):
        raise SystemExit("DATABASE_URL must be a postgresql+psycopg URL with a host and database")
    return parsed.render_as_string(hide_password=False)


def run_migrations_online() -> None:
    connection = config.attributes.get("connection")
    if connection is not None:
        _run(connection)
        return
    engine = create_engine(_url(), poolclass=pool.NullPool)
    # Only one migration run at a time: a second one waits here instead of colliding with the
    # first on roles, extensions, or the version table. The lock is held on its own connection
    # for the whole run and is released by the server if this process dies.
    with engine.connect() as guard:
        guard.exec_driver_sql("SELECT pg_advisory_lock(hashtext('shaidago.migrations'))")
        guard.commit()
        try:
            with engine.connect() as opened:
                _run(opened)
        finally:
            guard.exec_driver_sql("SELECT pg_advisory_unlock(hashtext('shaidago.migrations'))")
            guard.commit()


def _run(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_schemas=True,
        include_object=include_object,
        compare_type=True,
        # One transaction per revision so each revision can assume the owner role it sets.
        transaction_per_migration=True,
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    raise SystemExit("offline migrations are not supported: revisions run SQL that needs a server")
run_migrations_online()
