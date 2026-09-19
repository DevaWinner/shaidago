"""Empty database to head, one revision down and up, repeat runs, drift, and ownership."""

import psycopg
import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import Column, ForeignKey, Integer, MetaData, String, Table, create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.schema import CreateTable

from shaidago.db.metadata import NAMING_CONVENTION, metadata
from shaidago.db.migration_helpers import read_versioned_sql
from shaidago.db.revision import alembic_config, expected_head
from tests.integration.conftest import disposable_database

APPLICATION_ROLES = {
    "shaidago_owner",
    "shaidago_public",
    "shaidago_reviewer",
    "shaidago_worker",
    "shaidago_readonly_ops",
}


def exclude_version_table(
    _object: object, name: str | None, type_: str, _reflected: bool, _compare_to: object
) -> bool:
    return not (type_ == "table" and name == "alembic_version")


def render(url: URL) -> str:
    return url.render_as_string(hide_password=False)


@pytest.fixture
def empty_url(admin_connection: psycopg.Connection[tuple[object, ...]]):
    with disposable_database(admin_connection) as url:
        yield url


def query(url: URL, statement: str) -> list[tuple[object, ...]]:
    engine = create_engine(render(url))
    try:
        with engine.connect() as connection:
            return [tuple(row) for row in connection.execute(text(statement)).fetchall()]
    finally:
        engine.dispose()


def applied_revision(url: URL) -> list[object]:
    return [row[0] for row in query(url, "SELECT version_num FROM alembic_version")]


def test_empty_database_migrates_to_head_with_extension_roles_and_schemas(empty_url: URL) -> None:
    command.upgrade(alembic_config(render(empty_url)), "head")
    assert applied_revision(empty_url) == [expected_head()]
    assert query(empty_url, "SELECT extname FROM pg_extension WHERE extname = 'vector'") == [
        ("vector",)
    ]
    roles = {
        r[0]
        for r in query(empty_url, "SELECT rolname FROM pg_roles WHERE rolname LIKE 'shaidago_%'")
    }
    assert roles >= APPLICATION_ROLES
    schemas = {r[0] for r in query(empty_url, "SELECT nspname FROM pg_namespace")}
    assert {"app", "public_api"} <= schemas


def test_second_upgrade_is_a_no_op(empty_url: URL) -> None:
    config = alembic_config(render(empty_url))
    command.upgrade(config, "head")
    command.upgrade(config, "head")
    assert applied_revision(empty_url) == [expected_head()]


def test_head_can_step_down_and_up_again(empty_url: URL) -> None:
    config = alembic_config(render(empty_url))
    command.upgrade(config, "head")
    command.downgrade(config, "-1")
    assert query(empty_url, "SELECT version_num FROM alembic_version") == []
    assert query(empty_url, "SELECT 1 FROM pg_namespace WHERE nspname = 'app'") == []
    command.upgrade(config, "head")
    assert applied_revision(empty_url) == [expected_head()]


def test_migrated_database_matches_model_metadata(empty_url: URL) -> None:
    command.upgrade(alembic_config(render(empty_url)), "head")
    engine = create_engine(render(empty_url))
    try:
        with engine.connect() as connection:
            context = MigrationContext.configure(
                connection,
                opts={
                    "compare_type": True,
                    "include_schemas": True,
                    "include_object": exclude_version_table,
                },
            )
            assert compare_metadata(context, metadata) == []
    finally:
        engine.dispose()


def test_every_managed_object_is_owned_by_the_owner_role(empty_url: URL) -> None:
    command.upgrade(alembic_config(render(empty_url)), "head")
    not_owned = query(
        empty_url,
        "SELECT n.nspname, c.relname, pg_get_userbyid(c.relowner) FROM pg_class c "
        "JOIN pg_namespace n ON n.oid = c.relnamespace "
        "WHERE n.nspname IN ('app', 'public_api') AND c.relowner <> "
        "(SELECT oid FROM pg_roles WHERE rolname = 'shaidago_owner')",
    )
    assert not_owned == []
    schema_owners = query(
        empty_url,
        "SELECT nspname, pg_get_userbyid(nspowner) FROM pg_namespace "
        "WHERE nspname IN ('app', 'public_api') ORDER BY 1",
    )
    assert schema_owners == [("app", "shaidago_owner"), ("public_api", "shaidago_owner")]


def test_application_roles_can_read_the_applied_revision(empty_url: URL) -> None:
    command.upgrade(alembic_config(render(empty_url)), "head")
    engine = create_engine(render(empty_url))
    try:
        with engine.begin() as connection:
            for role in sorted(APPLICATION_ROLES - {"shaidago_owner"}):
                connection.execute(text(f"SET LOCAL ROLE {role}"))
                assert connection.execute(text("SELECT version_num FROM alembic_version")).all()
                connection.execute(text("RESET ROLE"))
    finally:
        engine.dispose()


def test_naming_convention_names_every_constraint_and_index() -> None:
    probe = MetaData(naming_convention=NAMING_CONVENTION)
    parent = Table(
        "parent",
        probe,
        Column("id", Integer, primary_key=True),
        Column("code", String, unique=True),
    )
    child = Table(
        "child",
        probe,
        Column("id", Integer, primary_key=True),
        Column("parent_id", Integer, ForeignKey(parent.c.id), index=True),
    )
    ddl = str(CreateTable(child)) + str(CreateTable(parent))
    assert "CONSTRAINT pk_child" in ddl
    assert "CONSTRAINT fk_child_parent_id_parent" in ddl
    assert "CONSTRAINT uq_parent_code" in ddl
    assert [index.name for index in child.indexes] == ["ix_child_parent_id"]
    assert metadata.naming_convention == NAMING_CONVENTION


def test_edited_baseline_sql_is_refused() -> None:
    with pytest.raises(RuntimeError, match="edited after"):
        read_versioned_sql("0001_security_baseline.sql", "0" * 64)
