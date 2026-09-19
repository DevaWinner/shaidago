"""Reporter-handle persistence for the insert-only public role.

Every credential check ends the same way for an unknown handle, a wrong passphrase, a deleted
handle, and a handle in backoff: no result, after one Argon2 verification and one bookkeeping
call. Failures are committed before the caller raises, so a rejected attempt still counts.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shaidago.auth.passwords import PasswordVerifier
from shaidago.reports.handles import (
    NewHandle,
    normalise_handle,
    normalise_passphrase,
)
from shaidago.shared.clock import Clock
from shaidago.shared.database import Database
from shaidago.shared.ids import IdGenerator

MAX_LISTED_REPORTS = 50
_INSERT = text(
    "INSERT INTO app.reporter_handles (id, handle, passphrase_hash, created_at) "
    "VALUES (:id, :handle, :hash, :now)"
)
_GET = text("SELECT id, passphrase_hash, backoff_until FROM app.reporter_handle_get(:handle)")
_FAILED = text("SELECT app.reporter_handle_record_failure(:id, :now)")
_SUCCEEDED = text("SELECT app.reporter_handle_record_success(:id, :today)")
_REPORTS = text(
    "SELECT status, status_updated_at, public_message FROM app.reporter_handle_reports(:id, :limit)"
)
_DELETE = text("SELECT app.reporter_handle_delete(:id)")


@dataclass(frozen=True)
class HandleReport:
    status: str
    status_updated_at: datetime
    message: str


async def insert_handle(
    session: AsyncSession,
    new: NewHandle,
    *,
    verifier: PasswordVerifier,
    clock: Clock,
    ids: IdGenerator,
) -> None:
    """Store the handle and the passphrase hash. The passphrase itself is never stored."""
    await session.execute(
        _INSERT,
        {
            "id": ids.new(),
            "handle": new.handle,
            "hash": verifier.hash(normalise_passphrase(new.passphrase)),
            "now": clock.now(),
        },
    )


@dataclass(frozen=True)
class HandleServices:
    verifier: PasswordVerifier
    clock: Clock
    ids: IdGenerator


async def authenticate(
    database: Database, services: HandleServices, *, handle: str, passphrase: str
) -> UUID | None:
    """The handle's internal ID when the credentials are right, else None (no reason given)."""
    canonical = normalise_handle(handle)
    verifier, now = services.verifier, services.clock.now()
    async with database.unit_of_work() as session:
        row = (await session.execute(_GET, {"handle": canonical or ""})).one_or_none()
        stored_hash = None if row is None else str(row.passphrase_hash)
        verification = verifier.verify(stored_hash, normalise_passphrase(passphrase))
        in_backoff = row is not None and row.backoff_until is not None and row.backoff_until > now
        accepted = row is not None and verification.matches and not in_backoff and canonical
        subject = (
            UUID(str(row.id)) if row is not None else services.ids.new()
        )  # matches no row if absent
        if accepted:
            await session.execute(_SUCCEEDED, {"id": subject, "today": now.date()})
        else:
            await session.execute(_FAILED, {"id": subject, "now": now})
    return subject if accepted else None


async def list_reports(session: AsyncSession, handle_id: UUID) -> list[HandleReport]:
    rows = await session.execute(_REPORTS, {"id": handle_id, "limit": MAX_LISTED_REPORTS})
    return [HandleReport(r.status, r.status_updated_at, r.public_message) for r in rows]


async def delete_handle(session: AsyncSession, handle_id: UUID) -> None:
    """Unlink every report, then remove the credential, in this one transaction."""
    await session.execute(_DELETE, {"id": handle_id})
