"""Tracking-code status lookup for the insert-only public role.

Only the keyed digests of the code leave this module. Every attempt, valid or not, issues exactly
one database call of the same shape, so an unknown code, a malformed code, and a real one cannot
be told apart by the response or (within the configured floor) by how long it took.
"""

import secrets
from dataclasses import dataclass
from datetime import datetime
from typing import Final

from sqlalchemy import ARRAY, LargeBinary, bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession

from shaidago.reports.tracking import (
    InvalidTrackingCodeError,
    lookup_candidates,
    normalise,
)

NEXT_ACTIONS: Final = {
    "received": "wait_for_review",
    "under_review": "wait_for_review",
    "needs_information": "answer_follow_up",
    "verified_for_public_update": "watch_public_updates",
    "referred": "see_escalation_guidance",
    "closed": "none",
}
_LOOKUP = text(
    "SELECT status, status_updated_at, public_message FROM app.tracking_lookup(:digests)"
).bindparams(bindparam("digests", type_=ARRAY(LargeBinary)))


_QUESTIONS = text(
    "SELECT question_id, question, state FROM app.tracking_follow_ups(:digests)"
).bindparams(bindparam("digests", type_=ARRAY(LargeBinary)))


@dataclass(frozen=True)
class TrackedQuestion:
    """A reviewer's question and only whether it was answered, never the answer."""

    question_id: str
    text: str
    state: str


@dataclass(frozen=True)
class TrackedReport:
    status: str
    status_updated_at: datetime
    message: str
    questions: tuple[TrackedQuestion, ...] = ()

    @property
    def next_action(self) -> str:
        return NEXT_ACTIONS[self.status]


def code_prefix(raw: str) -> str | None:
    """A safe rate-limit bucket for a code: its first group only, or None if unusable."""
    try:
        return normalise(raw).canonical[:5]
    except InvalidTrackingCodeError:
        return None


async def find_report(
    session: AsyncSession, raw_code: str, peppers: dict[str, bytes], active_version: str
) -> TrackedReport | None:
    """The tracked report, or None for any code that does not resolve.

    An invalid code still runs the query, with random digests of the same count, so the work done
    does not depend on whether the code was well formed.
    """
    try:
        digests = [
            digest for _, digest in lookup_candidates(peppers, active_version, normalise(raw_code))
        ]
    except InvalidTrackingCodeError:
        digests = [secrets.token_bytes(32) for _ in peppers]
    row = (await session.execute(_LOOKUP, {"digests": digests})).one_or_none()
    questions = (await session.execute(_QUESTIONS, {"digests": digests})).all()
    if row is None or row.status not in NEXT_ACTIONS:
        return None
    return TrackedReport(
        row.status,
        row.status_updated_at,
        row.public_message,
        tuple(TrackedQuestion(str(q.question_id), q.question, q.state) for q in questions),
    )
