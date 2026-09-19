"""Reviewer-authored public updates: draft, preview, confirm, withdraw.

Publishing is never a side effect of a status change. The preview returns the public projection
exactly as the public API would show it (same models), and confirmation must quote the preview's
digest, so a preview that no longer describes what would be published is a ``409``.
"""

from datetime import date, datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from shaidago.api.dependencies import Dependencies, get_dependencies, get_settings
from shaidago.api.reviewer_auth import AuthenticatedReviewer, require, reviewer_database
from shaidago.api.v1.projects import CitationOut, UpdateOut
from shaidago.api.v1.reviewer_reports import actor_of
from shaidago.auth.policy import Capability
from shaidago.review import publication
from shaidago.review.context import ReviewContext
from shaidago.shared.config import Settings
from shaidago.shared.problems import ProblemDetails

router = APIRouter(prefix="/reviewer/reports/{report_id}/public-updates", tags=["reviewer"])

DraftVerification = Literal[
    "verified_official", "corroborated", "community_reviewed", "disputed", "outdated"
]
PROBLEMS: dict[int | str, dict[str, Any]] = {
    400: {"model": ProblemDetails, "description": "The body could not be parsed."},
    401: {"model": ProblemDetails},
    403: {"model": ProblemDetails},
    404: {"model": ProblemDetails},
    409: {"model": ProblemDetails, "description": "Report not verified, not a draft, or stale."},
    422: {"model": ProblemDetails, "description": "Invalid fields or unmet requirements."},
    503: {"model": ProblemDetails},
}


class CitationIn(BaseModel):
    """An exact passage of an approved source version; the offset is computed, not trusted."""

    model_config = ConfigDict(extra="forbid")

    source_version_id: UUID
    passage: Annotated[str, Field(min_length=1, max_length=1000)]
    location_label: Annotated[str, Field(min_length=1, max_length=200)]


class DraftIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    statement: Annotated[str, Field(max_length=2100)]
    effective_on: date
    last_checked_on: date | None = None
    verification_state: DraftVerification
    citations: Annotated[list[CitationIn], Field(min_length=1, max_length=5)]


class PublishIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preview_digest: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class IssueOut(BaseModel):
    field: str
    code: str


class PreviewOut(BaseModel):
    """``update`` is the public projection as ``GET /v1/projects/{slug}`` would show it."""

    public_update_id: UUID
    state: str
    project_slug: str
    report_status: str
    report_version: int
    update: UpdateOut
    issues: list[IssueOut]
    can_publish: bool
    preview_digest: str


class PublishedOut(BaseModel):
    public_update_id: UUID
    project_slug: str
    published_at: datetime


class DraftSummaryOut(BaseModel):
    public_update_id: UUID
    state: str
    created_at: datetime


class DraftListOut(BaseModel):
    items: list[DraftSummaryOut]


def preview_out(preview: publication.Preview) -> PreviewOut:
    return PreviewOut(
        public_update_id=preview.draft_id,
        state=preview.state,
        project_slug=preview.project_slug,
        report_status=preview.report_status,
        report_version=preview.report_version,
        update=UpdateOut.model_validate(
            {
                "id": preview.draft_id,
                "statement": preview.statement,
                "effective_on": preview.effective_on,
                "last_checked_on": preview.last_checked_on,
                "verification_state": preview.verification_state,
                "information_class": preview.information_class,
                "citations": [
                    CitationOut.model_validate(vars(c), from_attributes=False)
                    for c in preview.citations
                ],
            }
        ),
        issues=[IssueOut(field=i.field, code=i.code) for i in preview.issues],
        can_publish=preview.state == "draft" and not preview.issues,
        preview_digest=preview.digest,
    )


@router.post(
    "",
    response_model=PreviewOut,
    status_code=201,
    responses=PROBLEMS,
    operation_id="reviewer_publication_create_draft",
)
async def create_draft(  # noqa: PLR0913 - a route names its collaborators
    report_id: UUID,
    body: DraftIn,
    *,
    request: Request,
    response: Response,
    reviewer: Annotated[AuthenticatedReviewer, Depends(require(Capability.PUBLIC_UPDATE_PUBLISH))],
    dependencies: Annotated[Dependencies, Depends(get_dependencies)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> PreviewOut:
    response.headers["Cache-Control"] = "no-store"
    actor = actor_of(reviewer, request)
    async with reviewer_database(dependencies).unit_of_work() as session:
        ctx = ReviewContext.build(session, dependencies, settings)
        draft_id = await publication.create_draft(
            ctx,
            actor,
            report_id,
            publication.DraftInput(
                body.statement,
                body.effective_on,
                body.last_checked_on,
                body.verification_state,
                tuple(
                    publication.CitationInput(c.source_version_id, c.passage, c.location_label)
                    for c in body.citations
                ),
            ),
        )
        preview = await publication.build_preview(ctx, actor, report_id, draft_id)
    return preview_out(preview)


@router.get(
    "", response_model=DraftListOut, responses=PROBLEMS, operation_id="reviewer_publication_list"
)
async def list_drafts(
    report_id: UUID,
    *,
    response: Response,
    _: Annotated[AuthenticatedReviewer, Depends(require(Capability.PUBLIC_UPDATE_PUBLISH))],
    dependencies: Annotated[Dependencies, Depends(get_dependencies)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> DraftListOut:
    response.headers["Cache-Control"] = "no-store"
    async with reviewer_database(dependencies).unit_of_work() as session:
        rows = await publication.list_drafts(
            ReviewContext.build(session, dependencies, settings), report_id
        )
    return DraftListOut(
        items=[DraftSummaryOut(public_update_id=i, state=s, created_at=c) for i, s, c in rows]
    )


# ":uuid" keeps ".../{id}:publish" from also matching this route (it would answer 401, not 405).
@router.get(
    "/{update_id:uuid}",
    response_model=PreviewOut,
    responses=PROBLEMS,
    operation_id="reviewer_publication_preview",
)
async def preview(  # noqa: PLR0913 - a route names its collaborators
    report_id: UUID,
    update_id: UUID,
    *,
    request: Request,
    response: Response,
    reviewer: Annotated[AuthenticatedReviewer, Depends(require(Capability.PUBLIC_UPDATE_PUBLISH))],
    dependencies: Annotated[Dependencies, Depends(get_dependencies)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> PreviewOut:
    response.headers["Cache-Control"] = "no-store"
    async with reviewer_database(dependencies).unit_of_work() as session:
        built = await publication.build_preview(
            ReviewContext.build(session, dependencies, settings),
            actor_of(reviewer, request),
            report_id,
            update_id,
        )
    return preview_out(built)


@router.post(
    "/{update_id}:publish",
    response_model=PublishedOut,
    responses=PROBLEMS,
    operation_id="reviewer_publication_publish",
)
async def publish(  # noqa: PLR0913 - a route names its collaborators
    report_id: UUID,
    update_id: UUID,
    body: PublishIn,
    *,
    request: Request,
    response: Response,
    reviewer: Annotated[AuthenticatedReviewer, Depends(require(Capability.PUBLIC_UPDATE_PUBLISH))],
    dependencies: Annotated[Dependencies, Depends(get_dependencies)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> PublishedOut:
    response.headers["Cache-Control"] = "no-store"
    actor = actor_of(reviewer, request)
    async with reviewer_database(dependencies).unit_of_work() as session:
        ctx = ReviewContext.build(session, dependencies, settings)
        published = await publication.publish(ctx, actor, report_id, update_id, body.preview_digest)
    return PublishedOut(
        public_update_id=published.public_update_id,
        project_slug=published.project_slug,
        published_at=published.published_at,
    )


@router.post(
    "/{update_id}:withdraw",
    status_code=204,
    responses=PROBLEMS,
    operation_id="reviewer_publication_withdraw",
)
async def withdraw(  # noqa: PLR0913 - a route names its collaborators
    report_id: UUID,
    update_id: UUID,
    *,
    request: Request,
    reviewer: Annotated[AuthenticatedReviewer, Depends(require(Capability.PUBLIC_UPDATE_PUBLISH))],
    dependencies: Annotated[Dependencies, Depends(get_dependencies)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    async with reviewer_database(dependencies).unit_of_work() as session:
        await publication.withdraw(
            ReviewContext.build(session, dependencies, settings),
            actor_of(reviewer, request),
            report_id,
            update_id,
        )
    return Response(status_code=204, headers={"Cache-Control": "no-store"})
