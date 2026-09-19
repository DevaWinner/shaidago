"""Enable application-role logins after migrations: ``python -m shaidago.db.provision``.

Reads the migration owner's ``DATABASE_URL`` and one password per role from the environment.
Deployed environments refuse placeholder passwords.
"""

import os
import sys
from collections.abc import Mapping

import psycopg
from psycopg import sql
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

from shaidago.db.roles import login_statement
from shaidago.shared.config import DEPLOYED_ENVIRONMENTS, PLACEHOLDER_PREFIX

PASSWORD_VARIABLES = {
    "shaidago_public": "DB_PASSWORD_PUBLIC",
    "shaidago_reviewer": "DB_PASSWORD_REVIEWER",
    "shaidago_worker": "DB_PASSWORD_WORKER",
    "shaidago_readonly_ops": "DB_PASSWORD_READONLY_OPS",
}


def provision(environ: Mapping[str, str]) -> list[str]:
    """Return the roles enabled, or raise ``ValueError`` naming the variable at fault."""
    owner_url = environ.get("DATABASE_URL", "")
    if not owner_url:
        raise ValueError("DATABASE_URL is not set")
    try:
        parsed_url = make_url(owner_url)
    except ArgumentError:
        raise ValueError("DATABASE_URL is not a valid database URL") from None
    deployed = environ.get("APP_ENV") in DEPLOYED_ENVIRONMENTS
    statements: list[tuple[str, sql.Composed]] = []
    for role, variable in PASSWORD_VARIABLES.items():
        password = environ.get(variable, "")
        if not password:
            raise ValueError(f"{variable} is not set")
        if deployed and PLACEHOLDER_PREFIX in password:
            raise ValueError(f"{variable} is a placeholder")
        try:
            statements.append((role, login_statement(role, password)))
        except ValueError as error:
            raise ValueError(f"{variable}: {error}") from None
    url = parsed_url.render_as_string(hide_password=False).replace("+psycopg", "")
    with psycopg.connect(url, autocommit=False) as connection:
        for _role, statement in statements:
            connection.execute(statement)
    return [role for role, _ in statements]


def main() -> int:
    try:
        roles = provision(os.environ)
    except ValueError as error:
        sys.stderr.write(f"provision: {error}\n")
        return 1
    sys.stdout.write(f"enabled login for {len(roles)} roles\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
