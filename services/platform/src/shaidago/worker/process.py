"""Run one discovery job to a stopping point, safely under duplicate delivery and crashes.

Every stage reads the run's status from PostgreSQL and continues from there, so a redelivered
message, or a worker that died between stages, resumes instead of repeating or skipping work. A
lease keeps two workers from running the same run; a delivery that cannot take the lease is
acknowledged and ignored. Cancellation is honoured between stages and keeps what was already
retrieved. A failure the pipeline marks permanent ends the run with a safe code; a transient one
is re-raised so the broker retries with backoff, and the broker's retry limit (with the attempt
cap here) means nothing retries forever.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Final, Protocol
from uuid import UUID

import structlog

from shaidago.worker.machine import ACTIVE
from shaidago.worker.store import MAX_ATTEMPTS, LostRunError, RunStore, RunView

_logger = structlog.get_logger("shaidago.worker")
EXHAUSTED: Final = "retries_exhausted"


class Outcome(StrEnum):
    SKIPPED = "skipped"
    COMPLETED = "completed"
    NEEDS_REVIEW = "needs_review"
    CANCELLED = "cancelled"
    FAILED = "failed"


class TransientStageError(Exception):
    """A dependency was briefly unavailable; the broker should retry later."""


class PermanentStageError(Exception):
    """The stage cannot succeed. ``code`` is a stable, content-free failure code."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class AnalysisResult:
    needs_review: bool


class DiscoveryPipeline(Protocol):
    """The stages of a run. Each must be safe to call again for the same run."""

    async def search(self, run: RunView, store: RunStore) -> None: ...

    async def analyse(self, run: RunView, store: RunStore) -> AnalysisResult: ...


async def process_run(
    store: RunStore, pipeline: DiscoveryPipeline, run_id: UUID, owner: str
) -> Outcome:
    structlog.contextvars.bind_contextvars(run_id=str(run_id))
    try:
        attempts = await store.acquire(run_id, owner)
        if attempts is None:
            return Outcome.SKIPPED
        run = await store.load(run_id)
        if run is None:
            return Outcome.SKIPPED
        if attempts > MAX_ATTEMPTS:
            await store.transition(run, "fail", failure_code="attempts_exhausted")
            return Outcome.FAILED
        try:
            return await _advance(store, pipeline, run)
        except PermanentStageError as error:
            latest = await store.load(run_id) or run
            await store.transition(latest, "fail", failure_code=error.code)
            return Outcome.FAILED
        except LostRunError:
            return Outcome.SKIPPED
        finally:
            # Also on a transient error, so the broker's retry can take the lease straight away.
            await store.release(run_id, owner)
    finally:
        structlog.contextvars.unbind_contextvars("run_id")


async def _advance(store: RunStore, pipeline: DiscoveryPipeline, run: RunView) -> Outcome:
    while True:
        if run.cancel_requested and run.status in ACTIVE:
            # Keep whatever was already retrieved; only future work stops.
            run = await store.transition(run, "cancel", on_behalf_of="reviewer")
        elif run.status == "queued":
            run = await store.transition(run, "start_search")
        elif run.status == "searching":
            await pipeline.search(run, store)
            run = await store.transition(await _reload(store, run), "start_analysis")
        elif run.status == "analysing":
            result = await pipeline.analyse(run, store)
            command = "require_review" if result.needs_review else "complete"
            run = await store.transition(await _reload(store, run), command)
        else:
            return {
                "complete": Outcome.COMPLETED,
                "needs_review": Outcome.NEEDS_REVIEW,
                "cancelled": Outcome.CANCELLED,
                "failed": Outcome.FAILED,
            }.get(run.status, Outcome.SKIPPED)


async def _reload(store: RunStore, run: RunView) -> RunView:
    latest = await store.load(run.id)
    if latest is None:
        raise LostRunError
    return latest


async def fail_exhausted(store: RunStore, run_id: UUID, code: str) -> None:
    """Mark a run failed when the broker gave up on its job. A no-op for a finished run."""
    run = await store.load(run_id)
    if run is not None and run.status in ACTIVE:
        await store.transition(run, "fail", failure_code=code)
