"""Reviewer capability policy: who may do what, independent of HTTP.

Deny by default: a capability not listed for a role is refused, and an unknown role has none.
The policy takes only a role and a capability, never a record ID, so a denial reveals nothing about
any record. There is no per-report assignment or tenant model in the pilot, so authorisation is
by role; if one is added, it extends ``authorize`` with an explicit scope argument and tests.
"""

from collections.abc import Mapping
from enum import StrEnum
from typing import Final

from shaidago.auth.sessions import Principal
from shaidago.shared.problems import FORBIDDEN, ProblemError


class Capability(StrEnum):
    QUEUE_READ = "queue_read"
    REPORT_DETAIL_READ = "report_detail_read"
    EVIDENCE_DOWNLOAD = "evidence_download"
    NOTE_WRITE = "note_write"
    STATUS_TRANSITION = "status_transition"
    DISCOVERY_RUN = "discovery_run"
    DISCOVERED_SOURCE_DECISION = "discovered_source_decision"
    PUBLIC_UPDATE_PUBLISH = "public_update_publish"
    SOURCE_REOPEN_SUPERSEDED = "source_reopen_superseded"
    REVIEWER_ADMIN = "reviewer_admin"


_BOTH: Final = frozenset({"reviewer", "admin"})
_ADMIN: Final = frozenset({"admin"})

POLICY: Final[Mapping[Capability, frozenset[str]]] = {
    Capability.QUEUE_READ: _BOTH,
    Capability.REPORT_DETAIL_READ: _BOTH,
    Capability.EVIDENCE_DOWNLOAD: _BOTH,
    Capability.NOTE_WRITE: _BOTH,
    Capability.STATUS_TRANSITION: _BOTH,
    Capability.DISCOVERY_RUN: _BOTH,
    Capability.DISCOVERED_SOURCE_DECISION: _BOTH,
    Capability.PUBLIC_UPDATE_PUBLISH: _BOTH,
    # From the controlled vocabulary: only an administrator may reopen a superseded source.
    Capability.SOURCE_REOPEN_SUPERSEDED: _ADMIN,
    Capability.REVIEWER_ADMIN: _ADMIN,
}


def is_allowed(role: str, capability: Capability) -> bool:
    return role in POLICY.get(capability, frozenset())


def authorize(principal: Principal, capability: Capability) -> None:
    """Raise the generic ``forbidden`` problem unless the principal's role has the capability."""
    if not is_allowed(principal.role, capability):
        raise ProblemError(FORBIDDEN)
