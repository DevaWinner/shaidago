"""What is deleted, when, and how.

* Expired or long-revoked reviewer sessions and expired idempotency records are deleted.
* Abandoned upload scratch files (``sg-upload-*``) older than an hour are removed.
* A report is *shredded* on request or after a configured age: every data key that protects its
  private text, contact, notes, answers, and decision reasons is destroyed (so the ciphertext left
  behind is permanently unreadable), its evidence objects and rows are deleted, and its contact
  ciphertext is cleared. Its status history and audit events stay (append-only), and nothing
  already published (a public update) is touched: publication is separate data by design.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Final
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shaidago.audit.events import AuditWriter
from shaidago.files.storage import ObjectStore
from shaidago.shared.clock import Clock
from shaidago.shared.ids import IdGenerator

SESSION_GRACE: Final = timedelta(days=7)
SCRATCH_MAX_AGE: Final = timedelta(hours=1)
SCRATCH_PREFIX: Final = "sg-upload-"

_SESSIONS = text(
    "DELETE FROM app.reviewer_sessions WHERE absolute_expires_at < :cutoff "
    "OR (revoked_at IS NOT NULL AND revoked_at < :cutoff)"
)
_IDEMPOTENCY = text("DELETE FROM app.idempotency_records WHERE expires_at < :now")
_REPORT = text("SELECT id, status FROM app.reports WHERE id = :id FOR UPDATE")
_KEYS = text(
    "SELECT description_key_id AS key_id FROM app.reports WHERE id = :r "
    "UNION SELECT data_key_id FROM app.report_contacts WHERE report_id = :r "
    "UNION SELECT data_key_id FROM app.report_notes WHERE report_id = :r "
    "UNION SELECT reason_key_id FROM app.report_status_events "
    "WHERE report_id = :r AND reason_key_id IS NOT NULL "
    "UNION SELECT data_key_id FROM app.report_follow_up_answers "
    "WHERE report_id = :r AND data_key_id IS NOT NULL "
    "UNION SELECT a.data_key_id FROM app.discovery_follow_up_answers a "
    "JOIN app.discovery_runs d ON d.id = a.run_id WHERE d.report_id = :r "
    "AND a.data_key_id IS NOT NULL "
    "UNION SELECT decision_key_id FROM app.discovered_sources "
    "WHERE report_id = :r AND decision_key_id IS NOT NULL"
)
_DESTROY = text(
    "UPDATE app.data_keys SET wrapped_key = NULL, kek_version = NULL, destroyed_at = :now "
    "WHERE id = ANY(:ids) AND destroyed_at IS NULL"
)
_CLEAR_CONTACT = text(
    "UPDATE app.report_contacts SET channel_ciphertext = NULL, value_ciphertext = NULL, "
    "destroyed_at = COALESCE(destroyed_at, :now) WHERE report_id = :r"
)
_EVIDENCE = text("SELECT id, object_key FROM app.evidence_files WHERE report_id = :r")
_DELETE_EVIDENCE = text("DELETE FROM app.evidence_files WHERE report_id = :r")
_OLD_CLOSED = text(
    "SELECT id FROM app.reports WHERE status = 'closed' AND status_updated_at < :cutoff "
    "ORDER BY status_updated_at, id LIMIT :limit"
)
_STALE_REVIEWERS = text(
    "SELECT id, role, last_sign_in_at FROM app.reviewers WHERE state = 'active' "
    "AND (last_sign_in_at IS NULL OR last_sign_in_at < :cutoff) ORDER BY id LIMIT 200"
)


@dataclass(frozen=True)
class PurgeCounts:
    sessions: int
    idempotency_records: int


@dataclass(frozen=True)
class ShredResult:
    report_id: UUID
    keys_destroyed: int
    evidence_removed: int


async def purge_expired(session: AsyncSession, clock: Clock) -> PurgeCounts:
    """Delete expired operational records. Repeating it changes nothing."""
    now = clock.now()
    sessions = await session.execute(_SESSIONS, {"cutoff": now - SESSION_GRACE})
    records = await session.execute(_IDEMPOTENCY, {"now": now})
    return PurgeCounts(
        sessions=int(getattr(sessions, "rowcount", 0) or 0),
        idempotency_records=int(getattr(records, "rowcount", 0) or 0),
    )


def sweep_scratch(directory: Path, now: datetime, max_age: timedelta = SCRATCH_MAX_AGE) -> int:
    """Remove abandoned upload scratch files older than ``max_age``. Returns how many."""
    removed = 0
    for path in directory.glob(f"{SCRATCH_PREFIX}*"):
        try:
            modified = datetime.fromtimestamp(path.stat().st_mtime, tz=now.tzinfo)
            if path.is_file() and now - modified > max_age:
                path.unlink()
                removed += 1
        except OSError:
            continue  # gone or unreadable: the next sweep decides again
    return removed


async def shred_report(
    session: AsyncSession, store: ObjectStore, clock: Clock, ids: IdGenerator, report_id: UUID
) -> ShredResult | None:
    """Make a report's private content permanently unreadable. None means no such report."""
    if (await session.execute(_REPORT, {"id": report_id})).one_or_none() is None:
        return None
    now = clock.now()
    key_ids = [row.key_id for row in (await session.execute(_KEYS, {"r": report_id})).all()]
    destroyed = 0
    if key_ids:
        result = await session.execute(_DESTROY, {"ids": key_ids, "now": now})
        destroyed = int(getattr(result, "rowcount", 0) or 0)
    await session.execute(_CLEAR_CONTACT, {"r": report_id, "now": now})
    files = (await session.execute(_EVIDENCE, {"r": report_id})).all()
    for row in files:
        await store.delete(row.object_key)  # deleting an absent object is not an error
    await session.execute(_DELETE_EVIDENCE, {"r": report_id})
    await AuditWriter(session, clock, ids).record(
        "report_shredded",
        actor_type="system",
        subject_type="report",
        subject_id=report_id,
        details={"keys_destroyed": destroyed, "evidence_removed": len(files)},
    )
    return ShredResult(report_id, destroyed, len(files))


async def shred_closed_reports(  # noqa: PLR0913 - keyword-only policy arguments
    session: AsyncSession,
    store: ObjectStore,
    clock: Clock,
    ids: IdGenerator,
    *,
    older_than: timedelta,
    limit: int = 100,
) -> list[ShredResult]:
    """Shred closed reports whose closing is older than ``older_than`` (at most ``limit``)."""
    cutoff = clock.now() - older_than
    rows = (await session.execute(_OLD_CLOSED, {"cutoff": cutoff, "limit": limit})).all()
    results: list[ShredResult] = []
    for row in rows:
        result = await shred_report(session, store, clock, ids, row.id)
        if result is not None and (result.keys_destroyed or result.evidence_removed):
            results.append(result)
    return results


async def stale_reviewers(session: AsyncSession, clock: Clock, inactive: timedelta) -> list[UUID]:
    """Active reviewers with no sign-in within ``inactive``: candidates for an access review."""
    rows = (await session.execute(_STALE_REVIEWERS, {"cutoff": clock.now() - inactive})).all()
    return [row.id for row in rows]
