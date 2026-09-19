"""Rewrap data keys under the active KEK (``make kek-rotate``).

Run as ``python -m shaidago.shared.rotate_keks``.

Reads ``DATABASE_URL`` (the migration owner), ``ENCRYPTION_KEKS`` and
``ENCRYPTION_ACTIVE_KEK_VERSION`` from the environment. Each batch is one transaction and one
audit event; re-running continues where an interrupted run stopped. Plaintext keys are never
printed or logged. Exit status 1 if any key could not be rewrapped.
"""

import asyncio
import os
import sys
from collections.abc import Mapping

from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

from shaidago.shared.clock import SystemClock
from shaidago.shared.config import CryptoSettings
from shaidago.shared.crypto import EnvironmentKekWrapper
from shaidago.shared.data_keys import DataKeyService, RotationResult
from shaidago.shared.database import Database, build_engine
from shaidago.shared.ids import Uuid7Generator

BATCH = 100


async def rotate_all(environ: Mapping[str, str]) -> RotationResult:
    try:
        url = make_url(environ.get("DATABASE_URL", ""))
    except ArgumentError:
        raise ValueError("DATABASE_URL is not a valid database URL") from None
    settings = CryptoSettings.model_validate(environ)
    wrapper = EnvironmentKekWrapper(settings.kek_keys().keys, settings.active_kek_version)
    engine = build_engine(url, application_name="kek-rotation", statement_timeout_ms=30_000)
    database = Database(engine)
    clock = SystemClock()
    total = RotationResult(0, 0, 0)
    try:
        while True:
            async with database.unit_of_work() as session:
                result = await DataKeyService(
                    session, wrapper, clock, Uuid7Generator(clock)
                ).rotate_and_audit(limit=BATCH)
            total = RotationResult(
                total.rewrapped + result.rewrapped, result.unavailable, result.remaining
            )
            if result.rewrapped == 0:
                return total
    finally:
        await engine.dispose()


def main() -> int:
    try:
        result = asyncio.run(rotate_all(os.environ))
    except (ValueError, KeyError) as error:
        sys.stderr.write(f"kek-rotate: {error}\n")
        return 1
    sys.stdout.write(
        f"rewrapped {result.rewrapped}; unavailable {result.unavailable}; "
        f"remaining {result.remaining}\n"
    )
    return 1 if result.unavailable else 0


if __name__ == "__main__":
    raise SystemExit(main())
