# ruff: noqa: T201, PLR2004
"""``python -m shaidago.retention``: operator retention commands (``make retention-purge``).

    purge                       delete expired sessions and idempotency records, sweep scratch files
    shred-report <report-id>    make one report's private content permanently unreadable
    shred-closed <days>         shred closed reports closed more than <days> days ago
    review-reviewers <days>     list active reviewers with no sign-in for <days> days

Uses ``DATABASE_URL`` (the migration owner) and the object store settings. Nothing here runs from
the API. Retention periods are chosen by the operator; none is a legal conclusion.
"""

import asyncio
import os
import sys
import tempfile
from datetime import timedelta
from pathlib import Path
from uuid import UUID

from shaidago.files.storage import S3ObjectStore
from shaidago.retention.purge import (
    purge_expired,
    shred_closed_reports,
    shred_report,
    stale_reviewers,
    sweep_scratch,
)
from shaidago.shared.clock import SystemClock
from shaidago.shared.config import load_settings
from shaidago.shared.database import Database, create_engine
from shaidago.shared.ids import Uuid7Generator


async def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    settings = load_settings(os.environ)
    engine = create_engine(settings.database, application_name="retention")
    database = Database(engine)
    clock = SystemClock()
    ids = Uuid7Generator(clock)
    storage = settings.storage
    store = S3ObjectStore(
        endpoint_url=storage.endpoint_url,
        bucket=storage.bucket,
        access_key_id=storage.access_key_id.get_secret_value(),
        secret_access_key=storage.secret_access_key.get_secret_value(),
        timeout_seconds=15.0,
    )
    try:
        command = argv[0]
        async with database.unit_of_work() as session:
            if command == "purge":
                counts = await purge_expired(session, clock)
                swept = sweep_scratch(Path(tempfile.gettempdir()), clock.now())
                line = f"sessions={counts.sessions} idempotency={counts.idempotency_records}"
                print(f"{line} scratch={swept}")
            elif command == "shred-report" and len(argv) == 2:
                result = await shred_report(session, store, clock, ids, UUID(argv[1]))
                print(
                    "not found"
                    if result is None
                    else f"keys={result.keys_destroyed} evidence={result.evidence_removed}"
                )
            elif command == "shred-closed" and len(argv) == 2:
                shredded = await shred_closed_reports(
                    session, store, clock, ids, older_than=timedelta(days=int(argv[1]))
                )
                print(f"reports shredded: {len(shredded)}")
            elif command == "review-reviewers" and len(argv) == 2:
                for reviewer_id in await stale_reviewers(
                    session, clock, timedelta(days=int(argv[1]))
                ):
                    print(reviewer_id)
            else:
                print(__doc__)
                return 2
    finally:
        await engine.dispose()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1:])))
