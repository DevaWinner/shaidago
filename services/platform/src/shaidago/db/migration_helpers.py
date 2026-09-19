"""Helpers for revision scripts. Keep revisions declarative and put shared rules here."""

import hashlib
from importlib.resources import files

from alembic import op

OWNER_ROLE = "shaidago_owner"


def use_owner_role() -> None:
    """Run the rest of this revision's transaction as the object owner (ADR-0003).

    Call first in every revision after the baseline, so tables, views, and functions are owned
    by ``shaidago_owner`` and the default privileges defined for that role apply to them.
    """
    op.execute(f"SET LOCAL ROLE {OWNER_ROLE}")


def read_versioned_sql(name: str, expected_sha256: str) -> str:
    """Read a packaged SQL file and refuse it if it changed since the revision was written."""
    data = files("shaidago.db.sql").joinpath(name).read_bytes()
    if hashlib.sha256(data).hexdigest() != expected_sha256:
        raise RuntimeError(f"{name} was edited after this revision was written; add a new revision")
    return data.decode("utf-8")


def run_sql_script(script: str) -> None:
    """Execute a multi-statement script without ``%`` parameter parsing, in the open transaction."""
    driver = op.get_bind().connection.driver_connection
    if driver is None:
        raise RuntimeError("database connection is closed")
    driver.execute(script)  # pyright: ignore[reportUnknownMemberType,reportAttributeAccessIssue]
