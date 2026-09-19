"""PostgreSQL persistence for a run's lease, stage, attempts, and progress."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Final
from uuid import UUID

from sqlalchemy import text

from shaidago.audit.events import AuditWriter
from shaidago.shared.clock import Clock
from shaidago.shared.database import Database
from shaidago.shared.ids import IdGenerator
from shaidago.worker.machine import find_transition

LEASE_SECONDS: Final = 300
MAX_ATTEMPTS: Final = 5

_ACQUIRE = text(
    "UPDATE app.discovery_runs SET lease_owner = :owner, lease_expires_at = :expires, "
    "attempts = attempts + 1, updated_at = :now "
    "WHERE id = :id AND status IN ('queued', 'searching', 'analysing') "
    "AND (lease_owner IS NULL OR lease_owner = :owner OR lease_expires_at < :now) "
    "RETURNING attempts"
)
_LOAD = text(
    "SELECT id, scope, project_id, report_id, status, attempts, cancel_requested, failure_code, "
    "provider_mode, demo_replay, query_text, results_found, fetched_count, analysed_count, "
    "version FROM app.discovery_runs WHERE id = :id"
)
_TRANSITION = text(
    "UPDATE app.discovery_runs SET status = :new, updated_at = :now, "
    "started_at = COALESCE(started_at, "
    " CASE WHEN :new = 'searching' THEN CAST(:now AS timestamptz) END), "
    "finished_at = CASE WHEN :new IN ('complete', 'failed', 'cancelled') "
    "THEN CAST(:now AS timestamptz) ELSE finished_at END, failure_code = :code, "
    "lease_owner = CASE WHEN :new IN ('complete', 'failed', 'cancelled') THEN NULL "
    "ELSE lease_owner END, "
    "lease_expires_at = CASE WHEN :new IN ('complete', 'failed', 'cancelled') THEN NULL "
    "ELSE lease_expires_at END "
    "WHERE id = :id AND status = :old"
)
_PROGRESS = text(
    "UPDATE app.discovery_runs SET results_found = :found, fetched_count = :fetched, "
    "analysed_count = :analysed, updated_at = :now WHERE id = :id"
)
_RELEASE = text(
    "UPDATE app.discovery_runs SET lease_owner = NULL, lease_expires_at = NULL, updated_at = :now "
    "WHERE id = :id AND lease_owner = :owner "
    "AND status NOT IN ('complete', 'failed', 'cancelled')"
)


@dataclass(frozen=True)
class RunView:
    id: UUID
    scope: str
    project_id: UUID
    report_id: UUID | None
    status: str
    attempts: int
    cancel_requested: bool
    failure_code: str | None
    provider_mode: str
    demo_replay: bool
    results_found: int
    fetched_count: int
    analysed_count: int
    version: int


class RunStore:
    """Every method is its own committed unit of work, so a crash between stages loses nothing."""

    def __init__(self, database: Database, clock: Clock, ids: IdGenerator) -> None:
        self._database = database
        self._clock = clock
        self._ids = ids

    @property
    def database(self) -> Database:
        return self._database

    def now(self) -> datetime:
        return self._clock.now()

    async def acquire(self, run_id: UUID, owner: str) -> int | None:
        """Take the lease and count the attempt; None when finished, absent, or held by another."""
        now = self._clock.now()
        async with self._database.unit_of_work() as session:
            row = (
                await session.execute(
                    _ACQUIRE,
                    {
                        "id": run_id,
                        "owner": owner,
                        "now": now,
                        "expires": now + timedelta(seconds=LEASE_SECONDS),
                    },
                )
            ).one_or_none()
        return None if row is None else int(row.attempts)

    async def load(self, run_id: UUID) -> RunView | None:
        async with self._database.unit_of_work() as session:
            row = (await session.execute(_LOAD, {"id": run_id})).one_or_none()
        if row is None:
            return None
        return RunView(
            row.id, row.scope, row.project_id, row.report_id, row.status, row.attempts,
            row.cancel_requested, row.failure_code, row.provider_mode, row.demo_replay,
            row.results_found, row.fetched_count, row.analysed_count, row.version,
        )  # fmt: skip

    async def transition(
        self,
        run: RunView,
        command: str,
        *,
        failure_code: str | None = None,
        on_behalf_of: str = "worker",
    ) -> RunView:
        """Apply a command: the pure machine decides, the database re-checks.

        ``on_behalf_of`` is the actor whose command this is (a cancellation is a reviewer's or
        reporter's request that the worker carries out); the audit event is always the worker's.
        """
        step = find_transition(run.status, command, on_behalf_of)
        now = self._clock.now()
        async with self._database.unit_of_work() as session:
            result = await session.execute(
                _TRANSITION,
                {
                    "id": run.id,
                    "old": run.status,
                    "new": step.to_status,
                    "now": now,
                    "code": failure_code,
                },
            )
            if not getattr(result, "rowcount", 0):
                raise LostRunError
            await AuditWriter(session, self._clock, self._ids).record(
                step.audit_event,
                actor_type="worker",
                subject_type="discovery_run",
                subject_id=run.id,
                details={"from": run.status, "to": step.to_status}
                | ({"failure_code": failure_code} if failure_code else {}),
            )
        refreshed = await self.load(run.id)
        if refreshed is None:
            raise LostRunError
        return refreshed

    async def progress(self, run_id: UUID, *, found: int, fetched: int, analysed: int) -> None:
        async with self._database.unit_of_work() as session:
            await session.execute(
                _PROGRESS,
                {"id": run_id, "found": found, "fetched": fetched, "analysed": analysed,
                 "now": self._clock.now()},
            )  # fmt: skip

    async def release(self, run_id: UUID, owner: str) -> None:
        async with self._database.unit_of_work() as session:
            await session.execute(
                _RELEASE, {"id": run_id, "owner": owner, "now": self._clock.now()}
            )


class LostRunError(Exception):
    """Another actor changed the run between the read and the write; the job stops quietly."""
