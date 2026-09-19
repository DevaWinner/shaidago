"""The discovered-source decision machine as pure data (a literal copy of the contract)."""

from dataclasses import dataclass
from typing import Final

_STAFF: Final = frozenset({"reviewer", "admin"})


@dataclass(frozen=True)
class Decision:
    from_state: str
    command: str
    to_state: str
    actors: frozenset[str]
    audit_event: str


DECISIONS: Final[tuple[Decision, ...]] = (
    Decision("not_reviewed", "attach", "attached", _STAFF, "discovered_source_attached"),
    Decision("not_reviewed", "reject", "rejected", _STAFF, "discovered_source_rejected"),
    Decision("not_reviewed", "defer", "deferred", _STAFF, "discovered_source_deferred"),
    Decision("deferred", "attach", "attached", _STAFF, "discovered_source_attached"),
    Decision("deferred", "reject", "rejected", _STAFF, "discovered_source_rejected"),
    Decision("attached", "reconsider", "deferred", _STAFF, "discovered_source_reconsidered"),
    Decision("rejected", "reconsider", "deferred", _STAFF, "discovered_source_reconsidered"),
)
COMMANDS: Final = tuple(dict.fromkeys(d.command for d in DECISIONS))
_BY_KEY: Final = {(d.from_state, d.command): d for d in DECISIONS}


class DecisionNotAllowedError(Exception):
    """The command does not exist from this state for this actor."""


def find_decision(state: str, command: str, actor: str) -> Decision:
    decision = _BY_KEY.get((state, command))
    if decision is None or actor not in decision.actors:
        raise DecisionNotAllowedError
    return decision
