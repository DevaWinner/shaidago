"""The report status state machine as pure data and one pure function.

The table is a literal copy of ``state_machines.report_status`` in
``contracts/controlled-vocabulary.json`` (a parity test compares them). Nothing here touches HTTP,
a database, or a clock, so the whole matrix can be tested exhaustively. Only reviewers and admins
drive it from the API; ``record_follow_up`` belongs to the reporter and is applied inside the
database function that stores the answer, so a reviewer asking for it is refused like any other
transition that does not exist.
"""

from dataclasses import dataclass
from typing import Final

TRANSITION_NOT_ALLOWED_CODE: Final = "report_status_transition_not_allowed"
ACTORS: Final = ("reviewer", "admin", "reporter", "system", "worker")
_STAFF: Final = frozenset({"reviewer", "admin"})


@dataclass(frozen=True)
class Transition:
    from_status: str
    command: str
    to_status: str
    actors: frozenset[str]
    audit_event: str


def _t(source: str, command: str, target: str, event: str = "report_status_changed") -> Transition:
    return Transition(source, command, target, _STAFF, event)


TRANSITIONS: Final[tuple[Transition, ...]] = (
    _t("received", "request_information", "needs_information"),
    _t("received", "start_review", "under_review"),
    _t("received", "close", "closed"),
    Transition(
        "needs_information",
        "record_follow_up",
        "under_review",
        frozenset({"reporter"}),
        "report_follow_up_received",
    ),
    _t("needs_information", "resume_review", "under_review"),
    _t("needs_information", "close", "closed"),
    _t("under_review", "request_information", "needs_information"),
    _t("under_review", "verify_for_public_update", "verified_for_public_update"),
    _t("under_review", "refer", "referred"),
    _t("under_review", "close", "closed"),
    _t("verified_for_public_update", "resume_review", "under_review", "report_status_reopened"),
    _t("verified_for_public_update", "refer", "referred"),
    _t("verified_for_public_update", "close", "closed"),
    _t("referred", "resume_review", "under_review", "report_status_reopened"),
    _t("referred", "close", "closed"),
    _t("closed", "reopen", "under_review", "report_status_reopened"),
)
COMMANDS: Final = tuple(dict.fromkeys(t.command for t in TRANSITIONS))
STATUSES: Final = (
    "received",
    "needs_information",
    "under_review",
    "verified_for_public_update",
    "referred",
    "closed",
)
# A reopening is a serious act on a closed report: it always carries a private reason.
REASON_REQUIRED: Final = frozenset({"reopen"})

_BY_KEY: Final = {(t.from_status, t.command): t for t in TRANSITIONS}


class TransitionNotAllowedError(Exception):
    """The command does not exist from this status for this actor. Carries no report data."""


def find_transition(status: str, command: str, actor: str) -> Transition:
    """The transition, or ``TransitionNotAllowedError``. Deny by default."""
    transition = _BY_KEY.get((status, command))
    if transition is None or actor not in transition.actors:
        raise TransitionNotAllowedError
    return transition
