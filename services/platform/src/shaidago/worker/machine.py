"""The discovery status machine as pure data (a literal copy of the controlled vocabulary)."""

from dataclasses import dataclass
from typing import Final

TERMINAL: Final = frozenset({"complete", "failed", "cancelled"})
ACTIVE: Final = frozenset({"queued", "searching", "analysing"})


@dataclass(frozen=True)
class Transition:
    from_status: str
    command: str
    to_status: str
    actors: frozenset[str]
    audit_event: str


_WORKER: Final = frozenset({"worker"})
_STAFF: Final = frozenset({"reviewer", "admin"})
_CANCEL: Final = frozenset({"reporter", "reviewer", "admin"})

TRANSITIONS: Final[tuple[Transition, ...]] = (
    Transition("queued", "start_search", "searching", _WORKER, "discovery_search_started"),
    Transition("queued", "cancel", "cancelled", _CANCEL, "discovery_cancelled"),
    Transition("queued", "fail", "failed", _WORKER, "discovery_failed"),
    Transition("searching", "start_analysis", "analysing", _WORKER, "discovery_analysis_started"),
    Transition("searching", "cancel", "cancelled", _CANCEL, "discovery_cancelled"),
    Transition("searching", "fail", "failed", _WORKER, "discovery_failed"),
    Transition("analysing", "complete", "complete", _WORKER, "discovery_completed"),
    Transition("analysing", "require_review", "needs_review", _WORKER, "discovery_review_required"),
    Transition("analysing", "cancel", "cancelled", _CANCEL, "discovery_cancelled"),
    Transition("analysing", "fail", "failed", _WORKER, "discovery_failed"),
    Transition(
        "needs_review", "approve_completion", "complete", _STAFF, "discovery_review_completed"
    ),
    Transition("needs_review", "reject_run", "failed", _STAFF, "discovery_failed"),
    Transition("needs_review", "cancel", "cancelled", _STAFF, "discovery_cancelled"),
)
_BY_KEY: Final = {(t.from_status, t.command): t for t in TRANSITIONS}


class DiscoveryTransitionNotAllowedError(Exception):
    """The command does not exist from this status for this actor."""


def find_transition(status: str, command: str, actor: str) -> Transition:
    transition = _BY_KEY.get((status, command))
    if transition is None or actor not in transition.actors:
        raise DiscoveryTransitionNotAllowedError
    return transition
