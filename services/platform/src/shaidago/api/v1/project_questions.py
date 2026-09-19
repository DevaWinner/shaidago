"""Public grounded project questions; answers are source-linked and never cacheable."""

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Request, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator

from shaidago.api.dependencies import Dependencies, get_dependencies, get_settings
from shaidago.api.rate_limits import enforce_rate_limit
from shaidago.api.v1.projects import reject_unknown_query, request_locale
from shaidago.projects.models import Locale
from shaidago.retrieval.questions import (
    ProjectQuestionNotFoundError,
    ProjectQuestionService,
    QuestionProviderUnavailableError,
    QuestionSource,
)
from shaidago.retrieval.search import RetrievalMode, normalise_query
from shaidago.shared.config import Settings
from shaidago.shared.problems import (
    DEPENDENCY_UNAVAILABLE,
    NOT_FOUND,
    QUESTION_ANSWERING_UNAVAILABLE,
    ProblemDetails,
    ProblemError,
)

router = APIRouter(prefix="/projects", tags=["projects"])
PROBLEMS: dict[int | str, dict[str, Any]] = {
    400: {"model": ProblemDetails},
    401: {"model": ProblemDetails},
    404: {"model": ProblemDetails},
    422: {"model": ProblemDetails},
    429: {"model": ProblemDetails},
    503: {"model": ProblemDetails},
}


class ProjectQuestionIn(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    question: str = Field(min_length=1, max_length=300)

    @field_validator("question")
    @classmethod
    def _safe_question(cls, value: str) -> str:
        return normalise_query(value)


class QuestionSourceOut(BaseModel):
    citation_id: str
    source_id: UUID
    title: str
    publisher: str
    url: str
    retrieved_at: datetime
    passage: str
    section_label: str | None


class QuestionStatementOut(BaseModel):
    text: str
    citation_ids: list[str]


class RetrievalOut(BaseModel):
    mode: RetrievalMode
    chunks_considered: int


class ProjectQuestionOut(BaseModel):
    answer: str
    statements: list[QuestionStatementOut]
    insufficient_evidence: bool
    confidence_note: str
    requested_locale: Locale
    served_locale: Locale
    generated_at: datetime
    retrieval: RetrievalOut
    sources: list[QuestionSourceOut]


def _source(value: QuestionSource) -> QuestionSourceOut:
    return QuestionSourceOut.model_validate(value, from_attributes=True)


@router.post("/{slug}/questions", response_model=ProjectQuestionOut, responses=PROBLEMS)
async def ask_project_question(  # noqa: PLR0913,PLR0917 - a route names its collaborators
    slug: Annotated[str, Path(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$", max_length=80)],
    body: ProjectQuestionIn,
    request: Request,
    response: Response,
    dependencies: Annotated[Dependencies, Depends(get_dependencies)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ProjectQuestionOut:
    response.headers["Cache-Control"] = "no-store"
    reject_unknown_query(request, frozenset())
    client = getattr(request.state, "client_hmac", None) or "unknown"
    await enforce_rate_limit(
        dependencies,
        f"sg:rl:qa:{client}",
        limit=settings.rate_limits.qa_per_hour,
    )
    database = dependencies.public_database
    model = dependencies.language_model
    if database is None or model is None:
        raise ProblemError(DEPENDENCY_UNAVAILABLE)
    service = ProjectQuestionService(
        database,
        model,
        dependencies.clock,
        dependencies.ids,
        elapsed=dependencies.monotonic,
    )
    try:
        result = await service.ask(
            project_slug=slug,
            question=body.question,
            locale=request_locale(request),
            request_id=request.state.request_id,
        )
    except ProjectQuestionNotFoundError:
        raise ProblemError(NOT_FOUND) from None
    except QuestionProviderUnavailableError:
        raise ProblemError(QUESTION_ANSWERING_UNAVAILABLE) from None
    answer = result.decision.answer
    return ProjectQuestionOut(
        answer=answer.answer,
        statements=[
            QuestionStatementOut(text=item.text, citation_ids=list(item.citation_ids))
            for item in answer.statements
        ],
        insufficient_evidence=answer.insufficient_evidence,
        confidence_note=answer.confidence_note,
        requested_locale=result.decision.requested_locale,
        served_locale=result.decision.served_locale,
        generated_at=answer.generated_at,
        retrieval=RetrievalOut(
            mode=result.retrieval_mode,
            chunks_considered=result.retrieved_chunks,
        ),
        sources=[_source(item) for item in result.sources],
    )
