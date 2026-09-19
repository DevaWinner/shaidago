"""Applies the security baseline and enables role logins for a deployment or local database."""

from importlib.resources import files

from psycopg import sql
from sqlalchemy.ext.asyncio import AsyncConnection

APPLICATION_ROLES = (
    "shaidago_public",
    "shaidago_reviewer",
    "shaidago_worker",
    "shaidago_readonly_ops",
)
OWNER_ROLE = "shaidago_owner"
MIN_PASSWORD_CHARS = 16


def baseline_sql() -> str:
    return files("shaidago.db.sql").joinpath("0001_security_baseline.sql").read_text("utf-8")


async def _execute_script(connection: AsyncConnection, script: str) -> None:
    """Run text containing ``%`` (for example ``format('%I')``) with no parameter parsing.

    Executes on the driver connection inside the caller's open transaction.
    """
    raw = await connection.get_raw_connection()
    driver = raw.driver_connection
    if driver is None:
        raise RuntimeError("database connection is closed")
    await driver.execute(script)  # pyright: ignore[reportUnknownMemberType]


async def apply_security_baseline(connection: AsyncConnection) -> None:
    """Run the baseline (idempotent). The caller controls the surrounding transaction."""
    await _execute_script(connection, baseline_sql())


def login_statement(role: str, password: str) -> sql.Composed:
    """The ALTER ROLE statement enabling login. Validates inputs; never logs the password."""
    if role not in APPLICATION_ROLES:
        raise ValueError("not an application role")
    if len(password) < MIN_PASSWORD_CHARS:
        raise ValueError("password is too short")
    # ALTER ROLE cannot take a bind parameter, so identifier and literal are rendered with
    # psycopg's own escaping.
    return sql.SQL("ALTER ROLE {} LOGIN PASSWORD {}").format(
        sql.Identifier(role), sql.Literal(password)
    )


async def enable_login(connection: AsyncConnection, role: str, password: str) -> None:
    """Give an application role a login password on an open SQLAlchemy connection."""
    statement = login_statement(role, password)
    raw = await connection.get_raw_connection()
    await _execute_script(connection, statement.as_string(raw.driver_connection))  # pyright: ignore[reportArgumentType]
