"""Public, read-only project endpoints.

Every response model is an allowlist: it names each field that may leave the service, so a new
column in a view or table can never reach a client by accident. Absent, hidden, and unpublished
records all return the same ``not_found`` problem.
"""

import hashlib
from datetime import date, datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from shaidago.api.dependencies import Dependencies, get_dependencies, get_settings
from shaidago.projects.catalogue import (
    MAX_QUERY_CHARS,
    Cited,
    ListFilters,
    PublicCatalogue,
)
from shaidago.projects.models import LOCALES, Locale
from shaidago.shared.config import Settings
from shaidago.shared.database import Database
from shaidago.shared.pagination import (
    CursorPosition,
    build_page,
    clamp_page_size,
    decode_cursor,
    scope_of,
)
from shaidago.shared.problems import (
    DEPENDENCY_UNAVAILABLE,
    NOT_FOUND,
    VALIDATION_FAILED,
    FieldError,
    ProblemDetails,
    ProblemError,
)

router = APIRouter(prefix="/projects", tags=["projects"])
localities_router = APIRouter(prefix="/localities", tags=["projects"])

Category = Literal[
    "health", "education", "water_sanitation", "roads_public_works", "other_public_service"
]
PublicStatus = Literal[
    "unknown", "planned", "procurement", "in_progress", "on_hold", "completed", "cancelled"
]
VerificationState = Literal[
    "verified_official", "corroborated", "community_reviewed", "disputed", "outdated"
]
SourceClass = Literal["official_source", "independent_source", "community_evidence_reviewed"]
CACHE_CONTROL = "public, max-age=60"
PROBLEMS: dict[int | str, dict[str, Any]] = {
    404: {"model": ProblemDetails},
    422: {"model": ProblemDetails},
}


class LocalityOut(BaseModel):
    slug: str
    name: str
    kind: Literal["state", "area_council"]
    parent_slug: str | None
    enabled_locales: list[Locale]


class ListParams(BaseModel):
    """Allowlisted list filters. Unknown query parameters are rejected, not ignored."""

    model_config = ConfigDict(extra="forbid")

    locality: Annotated[str | None, Field(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$", max_length=80)] = (
        None
    )
    category: Category | None = None
    status: PublicStatus | None = None
    verification: VerificationState | None = None
    q: Annotated[str | None, Field(min_length=1, max_length=MAX_QUERY_CHARS)] = None
    limit: Annotated[int | None, Field(ge=1, le=1000)] = None
    cursor: Annotated[str | None, Field(max_length=512)] = None


class LocalityListOut(BaseModel):
    items: list[LocalityOut]


class SummaryTextOut(BaseModel):
    title: str
    summary: str
    served_locale: Locale
    is_fallback: bool
    translation_status: Literal["reviewed", "machine_assisted"]


class ProjectSummaryOut(BaseModel):
    slug: str
    locality_slug: str
    category: Category
    public_status: PublicStatus
    last_checked_on: date | None
    updated_at: datetime
    text: SummaryTextOut


class ProjectPageOut(BaseModel):
    items: list[ProjectSummaryOut]
    next_cursor: str | None


class ProjectTextOut(SummaryTextOut):
    requested_locale: Locale
    promised_deliverable: str
    reviewed_at: datetime | None


class CitationOut(BaseModel):
    source_id: UUID
    source_title: str
    publisher: str
    canonical_url: str
    source_type: str
    information_class: Literal[
        "official_source", "independent_source", "community_evidence_reviewed"
    ]
    retrieved_at: datetime
    passage: str
    location_label: str


class FactOut(BaseModel):
    id: UUID
    kind: str
    statement: str
    effective_on: date | None
    last_checked_on: date | None
    verification_state: VerificationState
    information_class: Literal[
        "official_source", "independent_source", "community_evidence_reviewed"
    ]
    ai_generated: Literal[False] = False
    citations: list[CitationOut]


class UpdateOut(BaseModel):
    id: UUID
    statement: str
    effective_on: date | None
    last_checked_on: date | None
    verification_state: VerificationState
    information_class: Literal[
        "official_source", "independent_source", "community_evidence_reviewed"
    ]
    ai_generated: Literal[False] = False
    citations: list[CitationOut]


class ProjectDetailOut(BaseModel):
    slug: str
    locality_slug: str
    category: Category
    public_status: PublicStatus
    last_checked_on: date | None
    updated_at: datetime
    text: ProjectTextOut
    facts: list[FactOut]
    updates: list[UpdateOut]


class SourceOut(BaseModel):
    id: UUID
    canonical_url: str
    title: str
    publisher: str
    source_type: str
    information_class: Literal[
        "official_source", "independent_source", "community_evidence_reviewed"
    ]
    availability: str
    availability_checked_at: datetime | None


class ExcerptOut(BaseModel):
    cited_by: Literal["fact", "update"]
    item_id: UUID
    passage: str
    location_label: str


class SourceExcerptsOut(BaseModel):
    source: SourceOut
    excerpts: list[ExcerptOut]


def public_database(dependencies: Annotated[Dependencies, Depends(get_dependencies)]) -> Database:
    database = dependencies.public_database
    if database is None:
        raise ProblemError(DEPENDENCY_UNAVAILABLE)
    return database


def request_locale(request: Request) -> Locale:
    locale: str = request.state.locale
    return locale if locale in LOCALES else "en"  # type: ignore[return-value]  # LOCALES-checked


def reject_unknown_query(request: Request, allowed: frozenset[str]) -> None:
    unknown = sorted(set(request.query_params) - allowed)
    if unknown:
        raise ProblemError(
            VALIDATION_FAILED,
            field_errors=[
                FieldError(f"query.{name[:40]}", "unknown_parameter") for name in unknown
            ],
        )


def cacheable(request: Request, payload: BaseModel) -> Response:
    """JSON with a strong-enough validator: the ETag changes exactly when the body does."""
    body = payload.model_dump_json()
    etag = 'W/"' + hashlib.sha256(body.encode()).hexdigest()[:32] + '"'
    headers = {"ETag": etag, "Cache-Control": CACHE_CONTROL, "Vary": "X-Shaidago-Locale"}
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers=headers)
    return Response(content=body, media_type="application/json", headers=headers)


def _citation(row: object) -> CitationOut:
    return CitationOut.model_validate(row, from_attributes=True)


def _cited_fields(cited: Cited) -> dict[str, object]:
    row = cited.row
    return {
        "id": row.id,
        "statement": row.statement,
        "effective_on": row.effective_on,
        "last_checked_on": row.last_checked_on,
        "verification_state": row.verification_state,
        "information_class": cited.information_class,
        "citations": [_citation(c) for c in cited.citations],
    }


@localities_router.get("", response_model=LocalityListOut, responses=PROBLEMS)
async def list_localities(
    request: Request, database: Annotated[Database, Depends(public_database)]
) -> Response:
    reject_unknown_query(request, frozenset())
    async with database.unit_of_work() as session:
        rows = await PublicCatalogue(session).localities()
    items = [LocalityOut.model_validate(row, from_attributes=True) for row in rows]
    return cacheable(request, LocalityListOut(items=items))


@router.get("", response_model=ProjectPageOut, responses=PROBLEMS)
async def list_projects(
    request: Request,
    database: Annotated[Database, Depends(public_database)],
    settings: Annotated[Settings, Depends(get_settings)],
    params: Annotated[ListParams, Query()],
) -> Response:
    locale = request_locale(request)
    page_size = clamp_page_size(params.limit)
    key = settings.crypto.cursor_key()
    scope = scope_of(
        "/v1/projects",
        locality=params.locality,
        category=params.category,
        status=params.status,
        verification=params.verification,
        q=params.q,
        locale=locale,
    )
    after = None
    if params.cursor is not None:
        position = decode_cursor(key, scope, params.cursor)
        after = (datetime.fromisoformat(str(position.sort_value)), position.row_id)
    filters = ListFilters(
        locality=params.locality,
        category=params.category,
        status=params.status,
        verification=params.verification,
        query=params.q,
    )
    async with database.unit_of_work() as session:
        rows = await PublicCatalogue(session).list_projects(filters, locale, page_size + 1, after)
    page = build_page(
        rows,
        page_size,
        position_of=lambda row: CursorPosition(row.updated_at.isoformat(), row.id),
        key=key,
        scope=scope,
    )
    items = [
        ProjectSummaryOut(
            slug=row.slug,
            locality_slug=row.locality_slug,
            category=row.category,
            public_status=row.public_status,
            last_checked_on=row.last_checked_on,
            updated_at=row.updated_at,
            text=SummaryTextOut(
                title=row.title,
                summary=row.summary,
                served_locale=row.served_locale,
                is_fallback=row.served_locale != locale,
                translation_status=row.translation_status,
            ),
        )
        for row in page.items
    ]
    return cacheable(request, ProjectPageOut(items=items, next_cursor=page.next_cursor))


@router.get("/{slug}", response_model=ProjectDetailOut, responses=PROBLEMS)
async def get_project(
    slug: Annotated[str, Path(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$", max_length=80)],
    request: Request,
    database: Annotated[Database, Depends(public_database)],
) -> Response:
    reject_unknown_query(request, frozenset())
    locale = request_locale(request)
    async with database.unit_of_work() as session:
        detail = await PublicCatalogue(session).project(slug, locale)
    if detail is None:
        raise ProblemError(NOT_FOUND)
    served = detail.text
    payload = ProjectDetailOut(
        slug=detail.project.slug,
        locality_slug=detail.project.locality_slug,
        category=detail.project.category,
        public_status=detail.project.public_status,
        last_checked_on=detail.project.last_checked_on,
        updated_at=detail.project.updated_at,
        text=ProjectTextOut(
            title=served.title,
            summary=served.summary,
            served_locale=served.locale,
            is_fallback=served.locale != locale,
            translation_status=served.translation_status,
            requested_locale=locale,
            promised_deliverable=served.promised_deliverable,
            reviewed_at=served.reviewed_at,
        ),
        facts=[
            FactOut.model_validate({**_cited_fields(c), "kind": c.row.kind}) for c in detail.facts
        ],
        updates=[UpdateOut.model_validate(_cited_fields(c)) for c in detail.updates],
    )
    return cacheable(request, payload)


@router.get("/{slug}/sources/{source_id}", response_model=SourceExcerptsOut, responses=PROBLEMS)
async def get_project_source(
    slug: Annotated[str, Path(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$", max_length=80)],
    source_id: UUID,
    request: Request,
    database: Annotated[Database, Depends(public_database)],
) -> Response:
    reject_unknown_query(request, frozenset())
    async with database.unit_of_work() as session:
        view = await PublicCatalogue(session).source(slug, source_id)
    if view is None:
        raise ProblemError(NOT_FOUND)
    payload = SourceExcerptsOut(
        source=SourceOut.model_validate(view.source, from_attributes=True),
        excerpts=[ExcerptOut.model_validate(row, from_attributes=True) for row in view.excerpts],
    )
    return cacheable(request, payload)
