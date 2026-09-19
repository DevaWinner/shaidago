"""Cost bounds for anonymous discovery, as pure decisions.

One shared run per project per 24 hours; a global daily cap on fresh public runs; and, when the
cap is spent, the latest completed run is shown with its date instead of a hidden provider error.
The database function that creates public runs (BE-096) applies this decision atomically; keeping
the rule here makes every branch testable without a database.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Final, Literal

FRESH_WINDOW: Final = timedelta(hours=24)


@dataclass(frozen=True)
class PriorRun:
    run_id: str
    status: str
    created_at: datetime
    finished_at: datetime | None


@dataclass(frozen=True)
class BudgetDecision:
    action: Literal["reuse_fresh", "create", "show_latest_completed", "unavailable"]
    run_id: str | None = None


_IN_FLIGHT: Final = frozenset({"queued", "searching", "analysing", "needs_review"})


def decide_public_run(
    *,
    now: datetime,
    runs: list[PriorRun],
    fresh_runs_today: int,
    daily_limit: int,
) -> BudgetDecision:
    """Reuse a fresh or in-flight run; otherwise create one if budget remains.

    ``runs`` are this project's earlier public runs, newest first. A failed or cancelled run does
    not count as fresh. When the budget is spent the latest completed run is offered; with none
    to show, the honest answer is ``unavailable``.
    """
    for run in runs:
        if run.status in _IN_FLIGHT:
            return BudgetDecision("reuse_fresh", run.run_id)
        if run.status == "complete" and now - run.created_at < FRESH_WINDOW:
            return BudgetDecision("reuse_fresh", run.run_id)
    if fresh_runs_today < daily_limit:
        return BudgetDecision("create")
    for run in runs:
        if run.status == "complete":
            return BudgetDecision("show_latest_completed", run.run_id)
    return BudgetDecision("unavailable")
