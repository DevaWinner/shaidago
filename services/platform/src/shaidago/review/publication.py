"""Publishing a reviewer-authored update: a separate human act with its own record.

A status change never publishes. A reviewer writes neutral public text, cites approved source
passages, previews exactly what the public would see, and confirms that preview by its digest.
At confirmation everything is re-checked under row locks (role via the route, report status and
version, source approval, private references, guarded wording) and the public row and its citations
are written by one database function in the same transaction. Report text is never copied: the
public statement is what the reviewer wrote, checked against the private material so it cannot
repeat it.
"""

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Final
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import Row, text

from shaidago.audit.events import AuditWriter
from shaidago.review.context import ReviewContext
from shaidago.review.detail import Reviewer, read_contact
from shaidago.review.notes import list_notes
from shaidago.review.private_references import (
    PrivateContext,
    find_private_references,
    unsupported_terms,
)
from shaidago.shared.crypto import DecryptionError, field_context
from shaidago.shared.problems import (
    NOT_FOUND,
    PREVIEW_STALE,
    PUBLIC_UPDATE_NOT_DRAFT,
    PUBLIC_UPDATE_REPORT_NOT_VERIFIED,
    PUBLICATION_INCOMPLETE,
    VALIDATION_FAILED,
    FieldError,
    ProblemError,
)
from shaidago.sources.publication import Citation, publication_gaps

LAGOS: Final = ZoneInfo("Africa/Lagos")
VERIFIED_STATUS: Final = "verified_for_public_update"
CITABLE: Final = frozenset({"approved", "superseded"})
MAX_CITATIONS: Final = 5
MIN_STATEMENT_CHARS: Final = 10
MAX_STATEMENT_CHARS: Final = 2000
_CLASS_STRENGTH: Final = {
    "official_source": 0,
    "independent_source": 1,
    "community_evidence_reviewed": 2,
}

_REPORT = text(
    "SELECT r.status, r.version, r.project_id, r.anonymous, r.reporter_handle_id, "
    "r.description_ciphertext, r.description_key_id, r.schema_version, p.slug AS project_slug "
    "FROM app.reports r JOIN app.projects p ON p.id = r.project_id WHERE r.id = :id"
)
_VERSION = text(
    "SELECT v.review_state, strpos(v.content_text, :passage) AS position "
    "FROM app.source_versions v WHERE v.id = :id"
)
_INSERT_DRAFT = text(
    "INSERT INTO app.public_updates (id, report_id, project_id, statement, effective_on, "
    "last_checked_on, verification_state, state, authored_by, created_at, updated_at) VALUES "
    "(:id, :report, :project, :statement, :effective, :checked, :verification, 'draft', "
    ":author, :now, :now)"
)
_INSERT_CITATION = text(
    "INSERT INTO app.public_update_citations (id, public_update_id, source_version_id, passage, "
    "location_label, passage_start, created_at) VALUES "
    "(:id, :draft, :version, :passage, :label, :start, :now)"
)
_DRAFT = text(
    "SELECT d.id, d.state, d.statement, d.effective_on, d.last_checked_on, d.verification_state, "
    "d.project_id, d.created_at FROM app.public_updates d "
    "WHERE d.id = :id AND d.report_id = :report"
)
_LOCK = text(
    "SELECT d.id FROM app.public_updates d JOIN app.reports r ON r.id = d.report_id "
    "WHERE d.id = :id AND d.report_id = :report FOR UPDATE OF d, r"
)
_CITATIONS = text(
    "SELECT c.passage, c.location_label, v.review_state, v.retrieved_at, v.id AS "
    "source_version_id, s.id AS source_id, "
    "s.title AS source_title, s.publisher, s.canonical_url, s.source_type, s.information_class "
    "FROM app.public_update_citations c "
    "JOIN app.source_versions v ON v.id = c.source_version_id "
    "JOIN app.sources s ON s.id = v.source_id WHERE c.public_update_id = :id "
    "ORDER BY c.location_label, s.id"
)
_DRAFTS = text(
    "SELECT id, state, created_at FROM app.public_updates WHERE report_id = :report "
    "ORDER BY created_at DESC, id DESC LIMIT 50"
)
_ANSWERS = text(
    "SELECT a.id, a.answer_ciphertext, a.data_key_id, a.schema_version "
    "FROM app.report_follow_up_answers a WHERE a.report_id = :report AND a.kind = 'answered' "
    "LIMIT 50"
)
_REVIEWERS = text("SELECT identifier FROM app.reviewers ORDER BY identifier LIMIT 500")
_TRACK_RECORD = text("SELECT handle FROM app.reporter_handle_track_record(:id)")
_PUBLISH = text(
    "SELECT app.publish_public_update(:draft, :version, :actor_type, :actor, :now, :audit, "
    ":request)"
)
_WITHDRAW = text(
    "UPDATE app.public_updates SET state = 'withdrawn', updated_at = :now "
    "WHERE id = :id AND report_id = :report AND state = 'draft'"
)


@dataclass(frozen=True)
class CitationInput:
    source_version_id: UUID
    passage: str
    location_label: str


@dataclass(frozen=True)
class DraftInput:
    statement: str
    effective_on: date
    last_checked_on: date | None
    verification_state: str
    citations: tuple[CitationInput, ...]

    def __repr__(self) -> str:
        return "DraftInput(<redacted>)"


@dataclass(frozen=True)
class PreviewCitation:
    source_version_id: UUID
    source_id: UUID
    source_title: str
    publisher: str
    canonical_url: str
    source_type: str
    information_class: str
    retrieved_at: datetime
    passage: str
    location_label: str


@dataclass(frozen=True)
class Preview:
    """Exactly what the public projection would show, plus what stands in the way."""

    draft_id: UUID
    state: str
    project_slug: str
    report_status: str
    report_version: int
    statement: str
    effective_on: date
    last_checked_on: date | None
    verification_state: str
    information_class: str
    citations: tuple[PreviewCitation, ...]
    issues: tuple[FieldError, ...]
    digest: str

    def __repr__(self) -> str:
        return f"Preview(draft_id={self.draft_id}, state={self.state})"


@dataclass(frozen=True)
class Published:
    public_update_id: UUID
    project_slug: str
    published_at: datetime


def _today(ctx: ReviewContext) -> date:
    return ctx.clock.now().astimezone(LAGOS).date()


def _clean_statement(statement: str) -> str:
    cleaned = statement.strip()
    bad = not (MIN_STATEMENT_CHARS <= len(cleaned) <= MAX_STATEMENT_CHARS) or any(
        (c < " " and c not in "\n\t") or c == "\x7f" for c in cleaned
    )
    if bad or "<" in cleaned:
        raise ProblemError(
            VALIDATION_FAILED, field_errors=[FieldError("statement", "invalid_text")]
        )
    return cleaned


async def create_draft(
    ctx: ReviewContext, reviewer: Reviewer, report_id: UUID, data: DraftInput
) -> UUID:
    report = (await ctx.session.execute(_REPORT, {"id": report_id})).one_or_none()
    if report is None:
        raise ProblemError(NOT_FOUND)
    if report.status != VERIFIED_STATUS:
        raise ProblemError(PUBLIC_UPDATE_REPORT_NOT_VERIFIED)
    errors: list[FieldError] = []
    statement = _clean_statement(data.statement)
    if data.verification_state == "awaiting_verification":
        errors.append(FieldError("verification_state", "verification_required"))
    if data.last_checked_on is not None and data.last_checked_on > _today(ctx):
        errors.append(FieldError("last_checked_on", "date_in_future"))
    if not 1 <= len(data.citations) <= MAX_CITATIONS:
        errors.append(FieldError("citations", "one_to_five_required"))
    seen: set[tuple[UUID, str]] = set()
    located: list[tuple[CitationInput, int]] = []
    for index, citation in enumerate(data.citations[:MAX_CITATIONS]):
        field = f"citations.{index}"
        key = (citation.source_version_id, citation.location_label)
        if key in seen:
            errors.append(FieldError(field, "duplicate_citation"))
            continue
        seen.add(key)
        row = (
            await ctx.session.execute(
                _VERSION, {"id": citation.source_version_id, "passage": citation.passage}
            )
        ).one_or_none()
        if row is None or row.review_state not in CITABLE:
            errors.append(FieldError(f"{field}.source_version_id", "approved_source_required"))
        elif row.position < 1:
            errors.append(FieldError(f"{field}.passage", "passage_not_found"))
        else:
            located.append((citation, row.position - 1))
    if errors:
        raise ProblemError(PUBLICATION_INCOMPLETE, field_errors=errors)
    draft_id = ctx.ids.new()
    now = ctx.clock.now()
    await ctx.session.execute(
        _INSERT_DRAFT,
        {
            "id": draft_id,
            "report": report_id,
            "project": report.project_id,
            "statement": statement,
            "effective": data.effective_on,
            "checked": data.last_checked_on,
            "verification": data.verification_state,
            "author": reviewer.actor_id,
            "now": now,
        },
    )
    for citation, start in located:
        await ctx.session.execute(
            _INSERT_CITATION,
            {
                "id": ctx.ids.new(),
                "draft": draft_id,
                "version": citation.source_version_id,
                "passage": citation.passage,
                "label": citation.location_label,
                "start": start,
                "now": now,
            },
        )
    await AuditWriter(ctx.session, ctx.clock, ctx.ids).record(
        "public_update_drafted",
        actor_type=reviewer.actor_type,
        actor_id=reviewer.actor_id,
        subject_type="public_update",
        subject_id=draft_id,
        request_id=reviewer.request_id,
        details={"report_id": str(report_id)},
    )
    return draft_id


async def _private_context(
    ctx: ReviewContext, reviewer: Reviewer, report_id: UUID, report: Row[Any]
) -> PrivateContext:
    """Decrypt what a public statement must not repeat. Held in memory for this check only."""
    row = report
    texts: list[str] = []
    key_ids: list[UUID] = [row.description_key_id]
    answers = (await ctx.session.execute(_ANSWERS, {"report": report_id})).all()
    key_ids += [a.data_key_id for a in answers]
    keys = await ctx.keys.load_many(key_ids)
    try:
        key = keys.get(row.description_key_id)
        if key is not None:
            texts.append(
                ctx.cipher.decrypt(
                    key,
                    bytes(row.description_ciphertext),
                    field_context("reports", report_id, "description", row.schema_version),
                ).decode()
            )
        for answer in answers:
            answer_key = keys.get(answer.data_key_id)
            if answer_key is not None:
                texts.append(
                    ctx.cipher.decrypt(
                        answer_key,
                        bytes(answer.answer_ciphertext),
                        field_context(
                            "report_follow_up_answers", answer.id, "answer", answer.schema_version
                        ),
                    ).decode()
                )
    except DecryptionError:
        pass  # an unreadable value cannot be repeated
    texts += [body for _, _, _, body in await list_notes(ctx, report_id, 100, None) if body]
    contacts: list[str] = []
    if not row.anonymous:
        contact = await read_contact(ctx, report_id, reviewer)
        if contact is not None:
            contacts = [v for v in (contact.channel, contact.value) if v]
    handles: list[str] = []
    if row.reporter_handle_id is not None:
        track = (await ctx.session.execute(_TRACK_RECORD, {"id": report_id})).one_or_none()
        if track is not None:
            handles.append(track.handle)
    names = [r.identifier for r in (await ctx.session.execute(_REVIEWERS)).all()]
    return PrivateContext(tuple(texts), tuple(contacts), tuple(handles), tuple(names))


def _digest(parts: dict[str, object]) -> str:
    canonical = json.dumps(parts, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


async def build_preview(
    ctx: ReviewContext, reviewer: Reviewer, report_id: UUID, draft_id: UUID
) -> Preview:
    draft = (await ctx.session.execute(_DRAFT, {"id": draft_id, "report": report_id})).one_or_none()
    report = (await ctx.session.execute(_REPORT, {"id": report_id})).one_or_none()
    if draft is None or report is None:
        raise ProblemError(NOT_FOUND)
    rows = (await ctx.session.execute(_CITATIONS, {"id": draft_id})).all()
    all_citations = [
        Citation(r.source_id, r.publisher, r.information_class, r.review_state) for r in rows
    ]
    citable = [r for r in rows if r.review_state in CITABLE]
    citations = tuple(
        PreviewCitation(
            r.source_version_id,
            r.source_id,
            r.source_title,
            r.publisher,
            r.canonical_url,
            r.source_type,
            r.information_class,
            r.retrieved_at,
            r.passage,
            r.location_label,
        )
        for r in citable
    )
    issues: list[FieldError] = []
    if draft.state != "draft":
        issues.append(FieldError("state", "not_draft"))
    if report.status != VERIFIED_STATUS:
        issues.append(FieldError("report", "not_verified_for_public_update"))
    issues += publication_gaps(
        verification_state=draft.verification_state,
        citations=all_citations,
        effective_on=draft.effective_on,
        last_checked_on=draft.last_checked_on,
    )
    if draft.last_checked_on is not None and draft.last_checked_on > _today(ctx):
        issues.append(FieldError("last_checked_on", "date_in_future"))
    if draft.state == "draft":  # a settled draft no longer needs its private context decrypted
        private = await _private_context(ctx, reviewer, report_id, report)
        issues += [
            FieldError("statement", code)
            for code in find_private_references(draft.statement, private)
        ]
    issues += [
        FieldError("statement", f"unsupported_term_{term}")
        for term in unsupported_terms(draft.statement, [c.passage for c in citations])
    ]
    strongest = min(
        (c.information_class for c in citations),
        key=lambda value: _CLASS_STRENGTH.get(value, len(_CLASS_STRENGTH)),
        default="official_source",
    )
    body: dict[str, object] = {
        "id": draft.id,
        "project": report.project_slug,
        "statement": draft.statement,
        "effective_on": draft.effective_on,
        "last_checked_on": draft.last_checked_on,
        "verification_state": draft.verification_state,
        "information_class": strongest,
        "citations": [vars(c) for c in citations],
        "report_status": report.status,
        "report_version": report.version,
        "state": draft.state,
        "issues": [(i.field, i.code) for i in issues],
    }
    return Preview(
        draft_id=draft.id,
        state=draft.state,
        project_slug=report.project_slug,
        report_status=report.status,
        report_version=report.version,
        statement=draft.statement,
        effective_on=draft.effective_on,
        last_checked_on=draft.last_checked_on,
        verification_state=draft.verification_state,
        information_class=strongest,
        citations=citations,
        issues=tuple(issues),
        digest=_digest(body),
    )


async def publish(
    ctx: ReviewContext, reviewer: Reviewer, report_id: UUID, draft_id: UUID, confirmed_digest: str
) -> Published:
    """Confirm a preview. Raises a stable problem, and writes nothing, unless everything holds."""
    if (
        await ctx.session.execute(_LOCK, {"id": draft_id, "report": report_id})
    ).one_or_none() is None:
        raise ProblemError(NOT_FOUND)
    preview = await build_preview(ctx, reviewer, report_id, draft_id)
    if preview.state != "draft":
        raise ProblemError(PUBLIC_UPDATE_NOT_DRAFT)
    if preview.report_status != VERIFIED_STATUS:
        raise ProblemError(PUBLIC_UPDATE_REPORT_NOT_VERIFIED)
    if preview.digest != confirmed_digest:
        raise ProblemError(PREVIEW_STALE)
    if preview.issues:
        raise ProblemError(PUBLICATION_INCOMPLETE, field_errors=list(preview.issues))
    now = ctx.clock.now()
    outcome = (
        await ctx.session.execute(
            _PUBLISH,
            {
                "draft": draft_id,
                "version": preview.report_version,
                "actor_type": reviewer.actor_type,
                "actor": reviewer.actor_id,
                "now": now,
                "audit": ctx.ids.new(),
                "request": reviewer.request_id,
            },
        )
    ).scalar_one()
    if outcome == "published":
        return Published(draft_id, preview.project_slug, now)
    if outcome in {"stale", "report_state", "project_mismatch"}:
        raise ProblemError(
            PREVIEW_STALE if outcome == "stale" else PUBLIC_UPDATE_REPORT_NOT_VERIFIED
        )
    if outcome == "not_draft":
        raise ProblemError(PUBLIC_UPDATE_NOT_DRAFT)
    raise (
        ProblemError(NOT_FOUND)
        if outcome == "not_found"
        else ProblemError(
            PUBLICATION_INCOMPLETE,
            field_errors=[FieldError("citations", "approved_citation_required")],
        )
    )


async def withdraw(ctx: ReviewContext, reviewer: Reviewer, report_id: UUID, draft_id: UUID) -> None:
    result = await ctx.session.execute(
        _WITHDRAW, {"id": draft_id, "report": report_id, "now": ctx.clock.now()}
    )
    if not getattr(result, "rowcount", 0):
        exists = (
            await ctx.session.execute(_DRAFT, {"id": draft_id, "report": report_id})
        ).one_or_none()
        raise ProblemError(NOT_FOUND if exists is None else PUBLIC_UPDATE_NOT_DRAFT)
    await AuditWriter(ctx.session, ctx.clock, ctx.ids).record(
        "public_update_withdrawn",
        actor_type=reviewer.actor_type,
        actor_id=reviewer.actor_id,
        subject_type="public_update",
        subject_id=draft_id,
        request_id=reviewer.request_id,
        details={"report_id": str(report_id)},
    )


async def list_drafts(ctx: ReviewContext, report_id: UUID) -> list[tuple[UUID, str, datetime]]:
    report = (await ctx.session.execute(_REPORT, {"id": report_id})).one_or_none()
    if report is None:
        raise ProblemError(NOT_FOUND)
    rows = (await ctx.session.execute(_DRAFTS, {"report": report_id})).all()
    return [(r.id, r.state, r.created_at) for r in rows]
