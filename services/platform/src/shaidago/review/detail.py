"""The private report detail for an authorised reviewer.

The number of statements is fixed (a handful, whatever the report holds) and every list is
capped, so detail cannot become an N+1 or unbounded read. Only what a reviewer needs to act is
decrypted: the description and any follow-up answers. A contact is decrypted only when the caller
asks for it, through a database function that records the audit event before returning it.
Evidence rows expose metadata only, never the object key.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Row, text

from shaidago.audit.events import ActorType, AuditWriter
from shaidago.review.context import ReviewContext
from shaidago.shared.crypto import DataKey, DecryptionError, field_context

MAX_EVENTS = 200
MAX_QUESTIONS = 50
MAX_EVIDENCE = 20

_REPORT = text(
    "SELECT r.id, r.created_at, r.status, r.status_updated_at, r.concern_category, r.risk_level, "
    "r.version, r.anonymous, r.reporter_handle_id, r.description_ciphertext, "
    "r.description_key_id, r.schema_version, p.slug AS project_slug "
    "FROM app.reports r JOIN app.projects p ON p.id = r.project_id WHERE r.id = :id"
)
_EVENTS = text(
    "SELECT id, previous_status, new_status, public_message, actor_type, occurred_at, "
    "reason_ciphertext, reason_key_id, reason_schema_version "
    "FROM app.report_status_events WHERE report_id = :id "
    "ORDER BY occurred_at, id LIMIT :limit"
)
_QUESTIONS = text(
    "SELECT q.id, q.question, q.asked_at, q.withdrawn_at, a.id AS answer_id, a.kind, "
    "a.answer_ciphertext, a.data_key_id, a.schema_version "
    "FROM app.report_follow_up_questions q "
    "LEFT JOIN app.report_follow_up_answers a ON a.question_id = q.id "
    "WHERE q.report_id = :id ORDER BY q.asked_at, q.id LIMIT :limit"
)
_EVIDENCE = text(
    "SELECT id, display_name, sniffed_mime, size_bytes, sanitation_state, scan_state, created_at "
    "FROM app.evidence_files WHERE report_id = :id ORDER BY created_at, id LIMIT :limit"
)
_TRACK_RECORD = text("SELECT * FROM app.reporter_handle_track_record(:id)")
_CONTACT = text(
    "SELECT contact_id, channel_ciphertext, value_ciphertext, data_key_id, schema_version "
    "FROM app.reviewer_read_contact(:report, :actor_type, :actor, :now, :audit, :request)"
)


@dataclass(frozen=True)
class StatusEventView:
    event_id: UUID
    previous_status: str | None
    new_status: str
    public_message: str
    actor_type: str
    occurred_at: datetime
    internal_reason: str | None


@dataclass(frozen=True)
class FollowUpView:
    question_id: UUID
    question: str
    asked_at: datetime
    withdrawn: bool
    answer_kind: str | None
    answer: str | None


@dataclass(frozen=True)
class EvidenceView:
    id: UUID
    display_name: str
    mime_type: str
    size_bytes: int
    sanitation_state: str
    scan_state: str
    created_at: datetime


@dataclass(frozen=True)
class TrackRecordView:
    handle: str
    reports_total: int
    verified_for_public_update: int
    closed: int


@dataclass(frozen=True)
class ContactView:
    channel: str | None
    value: str | None

    def __repr__(self) -> str:
        return "ContactView(<redacted>)"


@dataclass(frozen=True)
class ReportDetail:
    id: UUID
    project_slug: str
    created_at: datetime
    status: str
    status_updated_at: datetime
    concern_category: str
    risk_level: str
    version: int
    has_contact: bool
    description: str
    events: list[StatusEventView]
    follow_ups: list[FollowUpView]
    evidence: list[EvidenceView]
    track_record: TrackRecordView | None
    contact: ContactView | None

    def __repr__(self) -> str:
        return f"ReportDetail(id={self.id})"


@dataclass(frozen=True)
class Reviewer:
    """Who is asking, for the audit event."""

    actor_type: ActorType
    actor_id: UUID
    request_id: str | None


async def load_detail(
    ctx: ReviewContext, report_id: UUID, reviewer: Reviewer, *, include_contact: bool
) -> ReportDetail | None:
    """The detail, or None for an unknown report. Records a view audit event on success."""
    session, crypto = ctx.session, ctx
    report = (await session.execute(_REPORT, {"id": report_id})).one_or_none()
    if report is None:
        return None
    events = (await session.execute(_EVENTS, {"id": report_id, "limit": MAX_EVENTS})).all()
    questions = (await session.execute(_QUESTIONS, {"id": report_id, "limit": MAX_QUESTIONS})).all()
    evidence = (await session.execute(_EVIDENCE, {"id": report_id, "limit": MAX_EVIDENCE})).all()
    track = None
    if report.reporter_handle_id is not None:
        row = (await session.execute(_TRACK_RECORD, {"id": report_id})).one_or_none()
        if row is not None:
            track = TrackRecordView(
                row.handle, row.reports_total, row.verified_for_public_update, row.closed
            )
    key_ids = (
        [report.description_key_id]
        + [q.data_key_id for q in questions if q.data_key_id]
        + [e.reason_key_id for e in events if e.reason_key_id]
    )
    keys = await crypto.keys.load_many(key_ids)
    description = _decrypt(
        crypto,
        keys.get(report.description_key_id),
        bytes(report.description_ciphertext),
        field_context("reports", report.id, "description", report.schema_version),
    )
    follow_ups = [_follow_up(crypto, keys, q) for q in questions]
    contact = await read_contact(ctx, report_id, reviewer) if include_contact else None
    await AuditWriter(session, ctx.clock, ctx.ids).record(
        "report_detail_viewed",
        actor_type=reviewer.actor_type,
        actor_id=reviewer.actor_id,
        subject_type="report",
        subject_id=report_id,
        request_id=reviewer.request_id,
        details={"contact_included": include_contact},
    )
    return ReportDetail(
        id=report.id,
        project_slug=report.project_slug,
        created_at=report.created_at,
        status=report.status,
        status_updated_at=report.status_updated_at,
        concern_category=report.concern_category,
        risk_level=report.risk_level,
        version=report.version,
        has_contact=not report.anonymous,
        description=description or "",
        events=[_event(crypto, keys, e) for e in events],
        follow_ups=follow_ups,
        evidence=[
            EvidenceView(e.id, e.display_name, e.sniffed_mime, e.size_bytes, e.sanitation_state,
                         e.scan_state, e.created_at)
            for e in evidence
        ],
        track_record=track,
        contact=contact,
    )  # fmt: skip


def _event(crypto: ReviewContext, keys: dict[UUID, DataKey], e: Row[Any]) -> StatusEventView:
    reason = None
    if e.reason_ciphertext is not None:
        reason = _decrypt(
            crypto,
            keys.get(e.reason_key_id),
            bytes(e.reason_ciphertext),
            field_context("report_status_events", e.id, "reason", e.reason_schema_version),
        )
    return StatusEventView(
        e.id, e.previous_status, e.new_status, e.public_message, e.actor_type, e.occurred_at, reason
    )


def _decrypt(
    crypto: ReviewContext, key: DataKey | None, ciphertext: bytes, context: bytes
) -> str | None:
    """Plaintext, or None when the key was destroyed or the value cannot be authenticated."""
    if key is None:
        return None
    try:
        return crypto.cipher.decrypt(key, ciphertext, context).decode()
    except DecryptionError:
        return None


def _follow_up(crypto: ReviewContext, keys: dict[UUID, DataKey], q: Row[Any]) -> FollowUpView:
    answer = None
    if q.answer_ciphertext is not None:
        answer = _decrypt(
            crypto,
            keys.get(q.data_key_id),
            bytes(q.answer_ciphertext),
            field_context("report_follow_up_answers", q.answer_id, "answer", q.schema_version),
        )
    return FollowUpView(
        question_id=q.id,
        question=q.question,
        asked_at=q.asked_at,
        withdrawn=q.withdrawn_at is not None,
        answer_kind=q.kind,
        answer=answer,
    )


async def read_contact(
    ctx: ReviewContext, report_id: UUID, reviewer: Reviewer
) -> ContactView | None:
    crypto = ctx
    row = (
        await ctx.session.execute(
            _CONTACT,
            {
                "report": report_id,
                "actor_type": reviewer.actor_type,
                "actor": reviewer.actor_id,
                "now": ctx.clock.now(),
                "audit": ctx.ids.new(),
                "request": reviewer.request_id,
            },
        )
    ).one_or_none()
    if row is None or row.data_key_id is None:
        return None
    key = (await crypto.keys.load_many([row.data_key_id])).get(row.data_key_id)
    version = row.schema_version
    fields: list[str | None] = []
    for name, ciphertext in (("channel", row.channel_ciphertext), ("value", row.value_ciphertext)):
        fields.append(
            None
            if ciphertext is None
            else _decrypt(
                crypto,
                key,
                bytes(ciphertext),
                field_context("report_contacts", row.contact_id, name, version),
            )
        )
    return ContactView(channel=fields[0], value=fields[1])
