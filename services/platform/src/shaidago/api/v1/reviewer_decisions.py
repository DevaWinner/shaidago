"""Reviewer status decisions and follow-up questions.

A decision names the status and version the reviewer saw; a stale view is a ``409`` and nothing is
written. The reporter-facing message and the private reason are separate fields. No route here
publishes anything.
"""

from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from shaidago.api.dependencies import Dependencies, get_dependencies, get_settings
from shaidago.api.reviewer_auth import AuthenticatedReviewer, require, reviewer_database
from shaidago.api.v1.reviewer_reports import ReportStatus, actor_of
from shaidago.audit.events import AuditWriter
from shaidago.auth.policy import Capability
from shaidago.review import follow_up_questions
from shaidago.review.context import ReviewContext
from shaidago.review.decisions import DecisionRequest, decide
from shaidago.shared.config import Settings
from shaidago.shared.problems import REPORT_TRANSITION_NOT_ALLOWED, ProblemDetails, ProblemError

router = APIRouter(prefix="/reviewer/reports/{report_id}", tags=["reviewer"])

# Literal copies of the state table's commands; a unit test compares them. ``record_follow_up`` is
# accepted so that asking for the reporter's transition is a refused command, not a bad request.
Command = Literal[
    "request_information",
    "start_review",
    "close",
    "resume_review",
    "verify_for_public_update",
    "refer",
    "reopen",
    "record_follow_up",
]
PROBLEMS: dict[int | str, dict[str, Any]] = {
    400: {"model": ProblemDetails, "description": "The body could not be parsed."},
    401: {"model": ProblemDetails},
    403: {"model": ProblemDetails},
    404: {"model": ProblemDetails},
    409: {"model": ProblemDetails, "description": "Stale view or transition not allowed."},
    422: {"model": ProblemDetails},
    503: {"model": ProblemDetails},
}


class TransitionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    command: Command
    expected_status: ReportStatus
    expected_version: Annotated[int, Field(ge=1)]
    # Private and encrypted; never shown to the reporter.
    internal_reason: Annotated[str, Field(max_length=1200)] | None = None
    # Shown to the reporter on tracking; a fixed default is used when omitted.
    reporter_message: Annotated[str, Field(max_length=400)] | None = None


class TransitionOut(BaseModel):
    report_id: UUID
    previous_status: str
    status: str
    version: int
    occurred_at: datetime
    published: Literal[False] = False


class QuestionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: Annotated[str, Field(max_length=600)]


class QuestionOut(BaseModel):
    question_id: UUID


@router.post("/status-transitions", response_model=TransitionOut, responses=PROBLEMS)
async def transition(  # noqa: PLR0913 - a route names its collaborators
    report_id: UUID,
    body: TransitionRequest,
    *,
    request: Request,
    response: Response,
    reviewer: Annotated[AuthenticatedReviewer, Depends(require(Capability.STATUS_TRANSITION))],
    dependencies: Annotated[Dependencies, Depends(get_dependencies)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> TransitionOut:
    response.headers["Cache-Control"] = "no-store"
    actor = actor_of(reviewer, request)
    database = reviewer_database(dependencies)
    try:
        async with database.unit_of_work() as session:
            result = await decide(
                ReviewContext.build(session, dependencies, settings),
                actor,
                report_id,
                DecisionRequest(
                    body.command,
                    body.expected_status,
                    body.expected_version,
                    body.internal_reason,
                    body.reporter_message,
                ),
            )
    except ProblemError as error:
        if error.problem is REPORT_TRANSITION_NOT_ALLOWED:
            # The refused command rolled back with its transaction; record the refusal on its own.
            async with database.unit_of_work() as session:
                await AuditWriter(session, dependencies.clock, dependencies.ids).record(
                    "report_status_change_denied",
                    actor_type=actor.actor_type,
                    actor_id=actor.actor_id,
                    subject_type="report",
                    subject_id=report_id,
                    outcome="denied",
                    request_id=actor.request_id,
                    details={"command": body.command, "status": body.expected_status},
                )
        raise
    return TransitionOut(
        report_id=result.report_id,
        previous_status=result.previous_status,
        status=result.status,
        version=result.version,
        occurred_at=result.occurred_at,
    )


@router.post(
    "/follow-up-questions", response_model=QuestionOut, status_code=201, responses=PROBLEMS
)
async def ask_follow_up(  # noqa: PLR0913 - a route names its collaborators
    report_id: UUID,
    body: QuestionRequest,
    *,
    request: Request,
    response: Response,
    reviewer: Annotated[AuthenticatedReviewer, Depends(require(Capability.STATUS_TRANSITION))],
    dependencies: Annotated[Dependencies, Depends(get_dependencies)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> QuestionOut:
    response.headers["Cache-Control"] = "no-store"
    async with reviewer_database(dependencies).unit_of_work() as session:
        question_id = await follow_up_questions.ask(
            ReviewContext.build(session, dependencies, settings),
            actor_of(reviewer, request),
            report_id,
            body.question,
        )
    return QuestionOut(question_id=question_id)


@router.post("/follow-up-questions/{question_id}:withdraw", status_code=204, responses=PROBLEMS)
async def withdraw_follow_up(  # noqa: PLR0913 - a route names its collaborators
    report_id: UUID,
    question_id: UUID,
    *,
    request: Request,
    reviewer: Annotated[AuthenticatedReviewer, Depends(require(Capability.STATUS_TRANSITION))],
    dependencies: Annotated[Dependencies, Depends(get_dependencies)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    async with reviewer_database(dependencies).unit_of_work() as session:
        await follow_up_questions.withdraw(
            ReviewContext.build(session, dependencies, settings),
            actor_of(reviewer, request),
            report_id,
            question_id,
        )
    return Response(status_code=204, headers={"Cache-Control": "no-store"})
