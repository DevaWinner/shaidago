"""Create the first reviewer: ``python -m shaidago.auth.bootstrap`` (``make reviewer-bootstrap``).

Credentials come only from the environment; nothing here or in ``.env.example`` is a usable
production password, and deployed environments refuse placeholders. The command never overwrites
an existing reviewer's password and never prints the password.
"""

import asyncio
import os
import sys
from collections.abc import Mapping

from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

from shaidago.auth.passwords import PasswordVerifier, WeakPasswordError
from shaidago.auth.reviewers import IdentifierError, ReviewerService, find_reviewer
from shaidago.shared.clock import SystemClock
from shaidago.shared.config import DEPLOYED_ENVIRONMENTS
from shaidago.shared.database import Database, build_engine
from shaidago.shared.ids import Uuid7Generator


class BootstrapError(Exception):
    """Configuration or input is unusable; the message names a variable, never a value."""


async def bootstrap(environ: Mapping[str, str]) -> str:
    """Returns "created" or "exists"; raises ``BootstrapError`` for a refused input."""
    owner_url = environ.get("DATABASE_URL", "")
    identifier = environ.get("REVIEWER_BOOTSTRAP_IDENTIFIER", "")
    password = environ.get("REVIEWER_BOOTSTRAP_PASSWORD", "")
    role = environ.get("REVIEWER_BOOTSTRAP_ROLE", "reviewer")
    for name, value in (
        ("DATABASE_URL", owner_url),
        ("REVIEWER_BOOTSTRAP_IDENTIFIER", identifier),
        ("REVIEWER_BOOTSTRAP_PASSWORD", password),
    ):
        if not value:
            raise BootstrapError(f"{name} is not set")
    if role not in ("reviewer", "admin"):
        raise BootstrapError("REVIEWER_BOOTSTRAP_ROLE must be reviewer or admin")
    try:
        url = make_url(owner_url)
    except ArgumentError:
        raise BootstrapError("DATABASE_URL is not a valid database URL") from None
    deployed = environ.get("APP_ENV") in DEPLOYED_ENVIRONMENTS
    engine = build_engine(url, application_name="reviewer-bootstrap", statement_timeout_ms=10_000)
    database = Database(engine)
    try:
        async with database.unit_of_work() as session:
            if await find_reviewer(session, identifier) is not None:
                return "exists"
            clock = SystemClock()
            service = ReviewerService(
                session,
                clock=clock,
                ids=Uuid7Generator(clock),
                passwords=PasswordVerifier(),
                deployed=deployed,
            )
            try:
                await service.create(
                    identifier, password, "admin" if role == "admin" else "reviewer"
                )
            except IdentifierError:
                raise BootstrapError("REVIEWER_BOOTSTRAP_IDENTIFIER is not acceptable") from None
            except WeakPasswordError as error:
                raise BootstrapError(f"REVIEWER_BOOTSTRAP_PASSWORD: {error}") from None
            return "created"
    finally:
        await engine.dispose()


def main() -> int:
    try:
        outcome = asyncio.run(bootstrap(os.environ))
    except BootstrapError as error:
        sys.stderr.write(f"reviewer-bootstrap: {error}\n")
        return 1
    sys.stdout.write(f"reviewer {outcome}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
