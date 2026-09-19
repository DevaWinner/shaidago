"""Alembic environment. Uses a plain sync engine; it never imports the FastAPI application."""

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool
from sqlalchemy.engine import Connection

from shaidago.db.metadata import metadata
from shaidago.shared.config import DatabaseSettings

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

# Each table module is imported here by the task that creates it, so it registers on `metadata`.
target_metadata = metadata

MANAGED_SCHEMAS = frozenset({"app", "public_api"})


def include_object(
    _object: object, name: str | None, type_: str, _reflected: bool, _compare_to: object
) -> bool:
    # Alembic's own version table is not part of the model.
    return not (type_ == "table" and name == "alembic_version")


def _url() -> str:
    override = config.attributes.get("url")
    if override is not None:
        return str(override)
    settings = DatabaseSettings.model_validate(os.environ)
    return settings.sqlalchemy_url().render_as_string(hide_password=False)


def run_migrations_online() -> None:
    connection = config.attributes.get("connection")
    if connection is not None:
        _run(connection)
        return
    engine = create_engine(_url(), poolclass=pool.NullPool)
    with engine.connect() as opened:
        _run(opened)


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
