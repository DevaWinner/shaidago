"""Reviewer queue and private report detail.

Every route needs a valid reviewer session and the matching capability (deny by default). Every
response is ``no-store``. The queue shows triage fields only; detail decrypts the description and
follow-up answers, and a contact only when ``include_contact=true`` is asked for, which needs its
own capability and writes an audit event before any ciphertext is returned.
"""

from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from shaidago.api.dependencies import Dependencies, get_dependencies, get_settings
from shaidago.api.reviewer_auth import AuthenticatedReviewer, require, reviewer_database
from shaidago.api.v1.projects import reject_unknown_query
from shaidago.auth.policy import Capability, authorize
from shaidago.review.context import ReviewContext
from shaidago.review.detail import Reviewer, load_detail
from shaidago.review.queue import QueueFilters, list_queue
from shaidago.shared.config import Settings
from shaidago.shared.pagination import (
    CursorPosition,
    build_page,
    clamp_page_size,
    decode_cursor,
    scope_of,
)
from shaidago.shared.problems import NOT_FOUND, ProblemDetails, ProblemError

router = APIRouter(prefix="/reviewer/reports", tags=["reviewer"])

ReportStatus = Literal[
    "received",
    "needs_information",
    "under_review",
    "verified_for_public_update",
    "referred",
    "closed",
]
RiskLevel = Literal["standard", "elevated", "high"]
ConcernCategory = Literal[
    "no_visible_work",
    "incomplete_work",
    "unsafe_construction",
    "suspected_incorrect_status",
    "access_barrier",
    "other_concern",
]
PROBLEMS: dict[int | str, dict[str, Any]] = {
    400: {"model": ProblemDetails, "description": "Invalid pagination cursor."},
    401: {"model": ProblemDetails},
    403: {"model": ProblemDetails},
    404: {"model": ProblemDetails},
    422: {"model": ProblemDetails},
    503: {"model": ProblemDetails},
}
QUEUE_PARAMETERS = frozenset(
    {"status", "risk_level", "concern_category", "project", "limit", "cursor"}
)


class QueueParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Annotated[list[ReportStatus] | None, Field(max_length=6)] = None
    risk_level: RiskLevel | None = None
    concern_category: ConcernCategory | None = None
    project: Annotated[str | None, Field(min_length=1, max_length=120, pattern=r"^[a-z0-9-]+$")] = (
        None
    )
    limit: Annotated[int | None, Field(ge=1, le=1000)] = None
    cursor: Annotated[str | None, Field(max_length=512)] = None


class QueueItemOut(BaseModel):
    report_id: UUID
    project_slug: str
    concern_category: str
    risk_level: str
    status: str
    version: int
    created_at: datetime
    status_updated_at: datetime
    has_contact: bool
    evidence_count: int
    open_follow_ups: int


class QueuePageOut(BaseModel):
    items: list[QueueItemOut]
    next_cursor: str | None


class StatusEventOut(BaseModel):
    previous_status: str | None
    new_status: str
    public_message: str
    actor_type: str
    occurred_at: datetime


class FollowUpOut(BaseModel):
    question_id: UUID
    question: str
    asked_at: datetime
    withdrawn: bool
    answer_kind: str | None
    answer: str | None


class EvidenceOut(BaseModel):
    """Metadata only: no object key, no URL. Content is fetched through the download broker."""

    evidence_id: UUID
    display_name: str
    mime_type: str
    size_bytes: int
    sanitation_state: str
    scan_state: str
    created_at: datetime


class TrackRecordOut(BaseModel):
    handle: str
    reports_total: int
    verified_for_public_update: int
    closed: int


class ContactOut(BaseModel):
    channel: str | None
    value: str | None


class ReportDetailOut(BaseModel):
    report_id: UUID
    project_slug: str
    concern_category: str
    risk_level: str
    status: str
    version: int
    created_at: datetime
    status_updated_at: datetime
    has_contact: bool
    description: str
    events: list[StatusEventOut]
    follow_ups: list[FollowUpOut]
    evidence: list[EvidenceOut]
    track_record: TrackRecordOut | None
    contact: ContactOut | None


def actor_of(reviewer: AuthenticatedReviewer, request: Request) -> Reviewer:
    return Reviewer(
        actor_type="admin" if reviewer.principal.role == "admin" else "reviewer",
        actor_id=reviewer.principal.reviewer_id,
        request_id=getattr(request.state, "request_id", None),
    )


@router.get("", response_model=QueuePageOut, responses=PROBLEMS)
async def queue(
    request: Request,
    response: Response,
    _: Annotated[AuthenticatedReviewer, Depends(require(Capability.QUEUE_READ))],
    dependencies: Annotated[Dependencies, Depends(get_dependencies)],
    settings: Annotated[Settings, Depends(get_settings)],
    params: Annotated[QueueParams, Query()],
) -> QueuePageOut:
    response.headers["Cache-Control"] = "no-store"
    reject_unknown_query(request, QUEUE_PARAMETERS)
    page_size = clamp_page_size(params.limit)
    key = settings.crypto.cursor_key()
    statuses = tuple(sorted(set(params.status or ())))
    scope = scope_of(
        "/v1/reviewer/reports",
        status=",".join(statuses),
        risk_level=params.risk_level,
        concern_category=params.concern_category,
        project=params.project,
    )
    after = None
    if params.cursor is not None:
        position = decode_cursor(key, scope, params.cursor)
        after = (datetime.fromisoformat(str(position.sort_value)), position.row_id)
    filters = QueueFilters(statuses, params.risk_level, params.concern_category, params.project)
    async with reviewer_database(dependencies).unit_of_work() as session:
        rows = await list_queue(session, filters, page_size + 1, after)
    page = build_page(
        rows,
        page_size,
        position_of=lambda row: CursorPosition(row.created_at.isoformat(), row.id),
        key=key,
        scope=scope,
    )
    return QueuePageOut(
        items=[
            QueueItemOut(
                report_id=row.id,
                project_slug=row.project_slug,
                concern_category=row.concern_category,
                risk_level=row.risk_level,
                status=row.status,
                version=row.version,
                created_at=row.created_at,
                status_updated_at=row.status_updated_at,
                has_contact=row.has_contact,
                evidence_count=row.evidence_count,
                open_follow_ups=row.open_follow_ups,
            )
            for row in page.items
        ],
        next_cursor=page.next_cursor,
    )


@router.get("/{report_id}", response_model=ReportDetailOut, responses=PROBLEMS)
async def detail(  # noqa: PLR0913 - a route names its collaborators
    report_id: UUID,
    request: Request,
    response: Response,
    *,
    reviewer: Annotated[AuthenticatedReviewer, Depends(require(Capability.REPORT_DETAIL_READ))],
    dependencies: Annotated[Dependencies, Depends(get_dependencies)],
    settings: Annotated[Settings, Depends(get_settings)],
    include_contact: bool = False,
) -> ReportDetailOut:
    response.headers["Cache-Control"] = "no-store"
    reject_unknown_query(request, frozenset({"include_contact"}))
    if include_contact:
        authorize(reviewer.principal, Capability.CONTACT_READ)
    async with reviewer_database(dependencies).unit_of_work() as session:
        found = await load_detail(
            ReviewContext.build(session, dependencies, settings),
            report_id,
            actor_of(reviewer, request),
            include_contact=include_contact,
        )
    if found is None:
        raise ProblemError(NOT_FOUND)
    return ReportDetailOut(
        report_id=found.id,
        project_slug=found.project_slug,
        concern_category=found.concern_category,
        risk_level=found.risk_level,
        status=found.status,
        version=found.version,
        created_at=found.created_at,
        status_updated_at=found.status_updated_at,
        has_contact=found.has_contact,
        description=found.description,
        events=[StatusEventOut(**vars(e)) for e in found.events],
        follow_ups=[FollowUpOut(**vars(f)) for f in found.follow_ups],
        evidence=[
            EvidenceOut(
                evidence_id=e.id,
                display_name=e.display_name,
                mime_type=e.mime_type,
                size_bytes=e.size_bytes,
                sanitation_state=e.sanitation_state,
                scan_state=e.scan_state,
                created_at=e.created_at,
            )
            for e in found.evidence
        ],
        track_record=TrackRecordOut(**vars(found.track_record)) if found.track_record else None,
        contact=ContactOut(**vars(found.contact)) if found.contact else None,
    )
