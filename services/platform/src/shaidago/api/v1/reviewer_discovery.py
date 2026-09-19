"""Reviewer Source Scout: approve an exact outbound query, run, review, and decide on sources.

A report-scoped run is created only from a query the reviewer approved verbatim (the approval is
the digest of the exact query and policy version; any change is a ``409`` and needs a new one).
Deciding to attach a discovered source creates a *pending* source that still needs the ordinary
source review; nothing here approves a fact or publishes anything.
"""

from datetime import date, datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from shaidago.api.dependencies import Dependencies, get_dependencies, get_settings
from shaidago.api.rate_limits import enforce_rate_limit
from shaidago.api.reviewer_auth import AuthenticatedReviewer, require, reviewer_database
from shaidago.api.v1.reviewer_reports import actor_of
from shaidago.auth.policy import Capability
from shaidago.discovery import service
from shaidago.discovery.analysis import LABEL
from shaidago.discovery.planner import POLICY_VERSION, approval_matches, plan_report_query
from shaidago.review.context import ReviewContext
from shaidago.shared.config import Settings
from shaidago.shared.problems import (
    DEPENDENCY_UNAVAILABLE,
    NOT_FOUND,
    VALIDATION_FAILED,
    FieldError,
    ProblemDetails,
    ProblemError,
)

router = APIRouter(prefix="/reviewer", tags=["reviewer"])
PROBLEMS: dict[int | str, dict[str, Any]] = {
    400: {"model": ProblemDetails},
    401: {"model": ProblemDetails},
    403: {"model": ProblemDetails},
    404: {"model": ProblemDetails},
    409: {"model": ProblemDetails},
    422: {"model": ProblemDetails},
    429: {"model": ProblemDetails},
    503: {"model": ProblemDetails},
}
Concept = Annotated[str, Field(min_length=1, max_length=80)]


class PlanIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    concepts: Annotated[list[Concept], Field(max_length=20)] = []


class RunCreateIn(PlanIn):
    approved_digest: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class TermOut(BaseModel):
    text: str
    source: str
    suggested_by: str


class RejectionOut(BaseModel):
    source: str
    reason: str


class PlanOut(BaseModel):
    """The exact outbound query, where each term came from, and what was excluded (and why)."""

    query: str
    terms: list[TermOut]
    rejected: list[RejectionOut]
    policy_version: str
    plan_digest: str


class RunCreatedOut(BaseModel):
    run_id: UUID
    status: str


class ReviewerSourceOut(BaseModel):
    source_id: UUID
    canonical_url: str
    publisher_domain: str
    title: str | None
    preliminary_type: str
    published_on: date | None
    published_provenance: str
    date_conflict: bool
    excerpt: str
    availability: str
    injection_flag: bool
    duplicate_of: UUID | None
    duplicate_kind: str | None
    disposition: str
    attached_source_id: UUID | None
    label: str = LABEL


class ReviewerRunOut(BaseModel):
    run_id: UUID
    scope: str
    report_id: UUID | None
    status: str
    version: int
    cancel_requested: bool
    failure_code: str | None
    query_text: str | None
    query_policy_version: str | None
    demo_replay: bool
    results_found: int
    fetched_count: int
    analysed_count: int
    created_at: datetime
    finished_at: datetime | None
    label: str = LABEL
    sources: list[ReviewerSourceOut]
    analysis: dict[str, Any] | None


class CancelOut(BaseModel):
    result: Literal["cancelled", "cancel_requested"]


class ReviewIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    command: Literal["approve_completion", "reject_run"]


class ReviewOut(BaseModel):
    status: str


class AnswerIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_index: Annotated[int, Field(ge=0, le=4)]
    kind: Literal["answered", "skipped", "unsafe"]
    answer: Annotated[str, Field(max_length=2100)] | None = None


class DecisionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    command: Literal["attach", "reject", "defer", "reconsider"]
    reason: Annotated[str, Field(max_length=400)]


class DecisionOut(BaseModel):
    disposition: str
    published: Literal[False] = False


async def _plan(ctx_db: Any, report_id: UUID, concepts: list[str]) -> tuple[Any, Any]:
    async with ctx_db.unit_of_work() as session:
        report = await service.report_project(session, report_id)
        if report is None:
            raise ProblemError(NOT_FOUND)
        terms = await service.project_terms(session, report.slug)
    if terms is None:
        raise ProblemError(NOT_FOUND)
    return report, plan_report_query(terms, concepts)


def _plan_out(plan: Any) -> PlanOut:
    return PlanOut(
        query=plan.query,
        terms=[
            TermOut(text=t.text, source=t.source, suggested_by=t.suggested_by) for t in plan.terms
        ],
        rejected=[RejectionOut(source=r.source, reason=r.reason) for r in plan.rejected],
        policy_version=plan.policy_version,
        plan_digest=plan.digest,
    )


@router.post("/reports/{report_id}/discovery-runs:plan", response_model=PlanOut, responses=PROBLEMS)
async def plan_run(
    report_id: UUID,
    body: PlanIn,
    *,
    response: Response,
    _: Annotated[AuthenticatedReviewer, Depends(require(Capability.DISCOVERY_RUN))],
    dependencies: Annotated[Dependencies, Depends(get_dependencies)],
) -> PlanOut:
    response.headers["Cache-Control"] = "no-store"
    _, plan = await _plan(reviewer_database(dependencies), report_id, list(body.concepts))
    return _plan_out(plan)


@router.post(
    "/reports/{report_id}/discovery-runs",
    response_model=RunCreatedOut,
    status_code=201,
    responses=PROBLEMS,
)
async def create_run(  # noqa: PLR0913 - a route names its collaborators
    report_id: UUID,
    body: RunCreateIn,
    *,
    request: Request,
    response: Response,
    reviewer: Annotated[AuthenticatedReviewer, Depends(require(Capability.DISCOVERY_RUN))],
    dependencies: Annotated[Dependencies, Depends(get_dependencies)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> RunCreatedOut:
    response.headers["Cache-Control"] = "no-store"
    if dependencies.job_queue is None:
        raise ProblemError(DEPENDENCY_UNAVAILABLE)
    database = reviewer_database(dependencies)
    report, plan = await _plan(database, report_id, list(body.concepts))
    if not plan.terms:
        raise ProblemError(
            VALIDATION_FAILED, field_errors=[FieldError("concepts", "no_safe_terms")]
        )
    if plan.digest != body.approved_digest or not approval_matches(
        plan, plan.query, POLICY_VERSION
    ):
        raise ProblemError(service.QUERY_CHANGED)
    await enforce_rate_limit(
        dependencies,
        f"sg:rl:discovery:reviewer:{reviewer.principal.reviewer_id}",
        limit=settings.rate_limits.discovery_reviewer_per_hour,
    )
    async with database.unit_of_work() as session:
        run_id = await service.create_report_run(
            ReviewContext.build(session, dependencies, settings),
            actor_of(reviewer, request),
            report,
            plan,
            provider_mode=settings.providers.mode,
        )
    await dependencies.job_queue.enqueue_discovery(run_id)
    return RunCreatedOut(run_id=run_id, status="queued")


@router.get("/discovery-runs/{run_id:uuid}", response_model=ReviewerRunOut, responses=PROBLEMS)
async def get_run(
    run_id: UUID,
    response: Response,
    _: Annotated[AuthenticatedReviewer, Depends(require(Capability.DISCOVERY_RUN))],
    dependencies: Annotated[Dependencies, Depends(get_dependencies)],
) -> ReviewerRunOut:
    response.headers["Cache-Control"] = "no-store"
    async with reviewer_database(dependencies).unit_of_work() as session:
        found = await service.reviewer_run_view(session, run_id)
    if found is None:
        raise ProblemError(NOT_FOUND)
    run, sources = found
    return ReviewerRunOut(
        run_id=run.id,
        scope=run.scope,
        report_id=run.report_id,
        status=run.status,
        version=run.version,
        cancel_requested=run.cancel_requested,
        failure_code=run.failure_code,
        query_text=run.query_text,
        query_policy_version=run.query_policy_version,
        demo_replay=run.demo_replay,
        results_found=run.results_found,
        fetched_count=run.fetched_count,
        analysed_count=run.analysed_count,
        created_at=run.created_at,
        finished_at=run.finished_at,
        sources=[
            ReviewerSourceOut(source_id=s.id, **{k: v for k, v in s._mapping.items() if k != "id"})
            for s in sources
        ],
        analysis=run.analysis,
    )


@router.post("/discovery-runs/{run_id}:cancel", response_model=CancelOut, responses=PROBLEMS)
async def cancel(  # noqa: PLR0913 - a route names its collaborators
    run_id: UUID,
    *,
    request: Request,
    response: Response,
    reviewer: Annotated[AuthenticatedReviewer, Depends(require(Capability.DISCOVERY_RUN))],
    dependencies: Annotated[Dependencies, Depends(get_dependencies)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> CancelOut:
    response.headers["Cache-Control"] = "no-store"
    async with reviewer_database(dependencies).unit_of_work() as session:
        result = await service.cancel_run(
            ReviewContext.build(session, dependencies, settings),
            actor_of(reviewer, request),
            run_id,
        )
    return CancelOut(result=result)  # type: ignore[arg-type]


@router.post("/discovery-runs/{run_id}:review", response_model=ReviewOut, responses=PROBLEMS)
async def review(  # noqa: PLR0913 - a route names its collaborators
    run_id: UUID,
    body: ReviewIn,
    *,
    request: Request,
    response: Response,
    reviewer: Annotated[AuthenticatedReviewer, Depends(require(Capability.DISCOVERY_RUN))],
    dependencies: Annotated[Dependencies, Depends(get_dependencies)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ReviewOut:
    response.headers["Cache-Control"] = "no-store"
    async with reviewer_database(dependencies).unit_of_work() as session:
        status = await service.review_run(
            ReviewContext.build(session, dependencies, settings),
            actor_of(reviewer, request),
            run_id,
            body.command,
        )
    return ReviewOut(status=status)


@router.post("/discovery-runs/{run_id}/follow-up-answers", status_code=204, responses=PROBLEMS)
async def answer_follow_up(  # noqa: PLR0913 - a route names its collaborators
    run_id: UUID,
    body: AnswerIn,
    *,
    request: Request,
    reviewer: Annotated[AuthenticatedReviewer, Depends(require(Capability.DISCOVERY_RUN))],
    dependencies: Annotated[Dependencies, Depends(get_dependencies)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    if (body.kind == "answered") != (body.answer is not None):
        raise ProblemError(VALIDATION_FAILED, field_errors=[FieldError("answer", "content")])
    async with reviewer_database(dependencies).unit_of_work() as session:
        await service.answer_follow_up(
            ReviewContext.build(session, dependencies, settings),
            actor_of(reviewer, request),
            run_id,
            body.question_index,
            body.kind,
            body.answer,
        )
    return Response(status_code=204, headers={"Cache-Control": "no-store"})


@router.post(
    "/discovered-sources/{source_id}/decision", response_model=DecisionOut, responses=PROBLEMS
)
async def decide(  # noqa: PLR0913 - a route names its collaborators
    source_id: UUID,
    body: DecisionIn,
    *,
    request: Request,
    response: Response,
    reviewer: Annotated[
        AuthenticatedReviewer, Depends(require(Capability.DISCOVERED_SOURCE_DECISION))
    ],
    dependencies: Annotated[Dependencies, Depends(get_dependencies)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> DecisionOut:
    response.headers["Cache-Control"] = "no-store"
    async with reviewer_database(dependencies).unit_of_work() as session:
        state = await service.decide_source(
            ReviewContext.build(session, dependencies, settings),
            actor_of(reviewer, request),
            source_id,
            body.command,
            body.reason,
        )
    return DecisionOut(disposition=state)
