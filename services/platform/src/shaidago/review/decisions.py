"""Reviewer status decisions: one transaction, one append-only event, one projection update.

The report row is locked, the caller's expected status and version are compared, the pure state
machine decides, and the event and the new projection are written together. The reviewer's private
reason is encrypted into the event; the reporter-facing message is separate plain text that the
tracking lookup shows. A decision never publishes anything: publication is a different act
(``review/publication.py``) with its own record.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Final
from uuid import UUID

from sqlalchemy import LargeBinary, bindparam, text

from shaidago.audit.events import AuditWriter
from shaidago.review.context import ReviewContext
from shaidago.review.detail import Reviewer
from shaidago.review.state_machine import (
    REASON_REQUIRED,
    TransitionNotAllowedError,
    find_transition,
)
from shaidago.shared.crypto import field_context
from shaidago.shared.problems import (
    NOT_FOUND,
    REPORT_TRANSITION_NOT_ALLOWED,
    REPORT_VERSION_CONFLICT,
    VALIDATION_FAILED,
    FieldError,
    ProblemError,
)

SCHEMA_VERSION: Final = 1
EVENT_TABLE: Final = "report_status_events"
MIN_TEXT_CHARS: Final = 5
MAX_REASON_CHARS: Final = 1000
MAX_MESSAGE_CHARS: Final = 300

DEFAULT_MESSAGES: Final = {
    "request_information": "We need a little more information. Please see the questions below.",
    "start_review": "A reviewer has started reviewing your report. It remains private.",
    "close": "Your report has been closed. It remains private and nothing was published.",
    "resume_review": "Review of your report has resumed.",
    "verify_for_public_update": "A reviewer has checked your report. Nothing has been published.",
    "refer": "Your report has been referred. It remains private and nothing was published.",
    "reopen": "Your report has been reopened for review.",
}

_LOCK = text(
    "SELECT r.status, r.version, "
    "(SELECT max(e.occurred_at) FROM app.report_status_events e WHERE e.report_id = r.id) "
    "AS latest_event_at FROM app.reports r WHERE r.id = :id FOR UPDATE OF r"
)
_EVENT = text(
    "INSERT INTO app.report_status_events (id, report_id, previous_status, new_status, "
    "public_message, actor_type, actor_id, occurred_at, reason_ciphertext, reason_key_id, "
    "reason_schema_version) VALUES (:id, :report, :previous, :new, :message, :actor_type, "
    ":actor, :at, :reason, :key, :version)"
).bindparams(bindparam("reason", type_=LargeBinary))
_PROJECT = text(
    "UPDATE app.reports SET status = :new, status_updated_at = :at, updated_at = :at WHERE id = :id"
)
_VERSION = text("SELECT version FROM app.reports WHERE id = :id")


@dataclass(frozen=True)
class DecisionRequest:
    command: str
    expected_status: str
    expected_version: int
    internal_reason: str | None = None
    reporter_message: str | None = None

    def __repr__(self) -> str:
        return f"DecisionRequest(command={self.command})"


@dataclass(frozen=True)
class DecisionResult:
    report_id: UUID
    event_id: UUID
    previous_status: str
    status: str
    version: int
    occurred_at: datetime


def _clean(value: str | None, field: str, maximum: int) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not (MIN_TEXT_CHARS <= len(cleaned) <= maximum) or any(
        c < " " and c not in "\n\t" for c in cleaned
    ):
        raise ProblemError(VALIDATION_FAILED, field_errors=[FieldError(field, "invalid_text")])
    return cleaned


async def decide(
    ctx: ReviewContext, reviewer: Reviewer, report_id: UUID, request: DecisionRequest
) -> DecisionResult:
    """Apply one reviewer command. Raises a stable problem; nothing is half-applied."""
    reason = _clean(request.internal_reason, "internal_reason", MAX_REASON_CHARS)
    message = _clean(request.reporter_message, "reporter_message", MAX_MESSAGE_CHARS)
    if reason is None and request.command in REASON_REQUIRED:
        raise ProblemError(
            VALIDATION_FAILED, field_errors=[FieldError("internal_reason", "required")]
        )
    row = (await ctx.session.execute(_LOCK, {"id": report_id})).one_or_none()
    if row is None:
        raise ProblemError(NOT_FOUND)
    if row.status != request.expected_status or row.version != request.expected_version:
        raise ProblemError(REPORT_VERSION_CONFLICT)
    try:
        transition = find_transition(row.status, request.command, reviewer.actor_type)
    except TransitionNotAllowedError:
        raise ProblemError(REPORT_TRANSITION_NOT_ALLOWED) from None
    now = ctx.clock.now()
    if row.latest_event_at is not None and now <= row.latest_event_at:
        # The projection check orders events by time; never let a skewed clock reorder history.
        now = row.latest_event_at + timedelta(microseconds=1)
    event_id = ctx.ids.new()
    ciphertext: bytes | None = None
    key_id: UUID | None = None
    if reason is not None:
        key = await ctx.keys.create(EVENT_TABLE, event_id, "review_notes")
        key_id = key.id
        ciphertext = ctx.cipher.encrypt(
            key,
            reason.encode(),
            field_context(EVENT_TABLE, event_id, "reason", SCHEMA_VERSION),
        )
    await ctx.session.execute(
        _EVENT,
        {
            "id": event_id,
            "report": report_id,
            "previous": row.status,
            "new": transition.to_status,
            "message": message or DEFAULT_MESSAGES[request.command],
            "actor_type": reviewer.actor_type,
            "actor": reviewer.actor_id,
            "at": now,
            "reason": ciphertext,
            "key": key_id,
            "version": SCHEMA_VERSION if ciphertext is not None else None,
        },
    )
    await ctx.session.execute(_PROJECT, {"id": report_id, "new": transition.to_status, "at": now})
    version = (await ctx.session.execute(_VERSION, {"id": report_id})).scalar_one()
    await AuditWriter(ctx.session, ctx.clock, ctx.ids).record(
        transition.audit_event,
        actor_type=reviewer.actor_type,
        actor_id=reviewer.actor_id,
        subject_type="report",
        subject_id=report_id,
        request_id=reviewer.request_id,
        details={
            "command": request.command,
            "previous_status": row.status,
            "new_status": transition.to_status,
            "previous_version": row.version,
            "new_version": int(version),
            "reason_recorded": reason is not None,
        },
    )
    return DecisionResult(report_id, event_id, row.status, transition.to_status, int(version), now)
