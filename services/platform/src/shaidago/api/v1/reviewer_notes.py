"""Reviewer notes: append-only, encrypted, never part of any public or tracking response."""

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from shaidago.api.dependencies import Dependencies, get_dependencies, get_settings
from shaidago.api.reviewer_auth import AuthenticatedReviewer, require, reviewer_database
from shaidago.api.v1.projects import reject_unknown_query
from shaidago.api.v1.reviewer_reports import actor_of
from shaidago.auth.policy import Capability
from shaidago.review import notes
from shaidago.review.context import ReviewContext
from shaidago.shared.config import Settings
from shaidago.shared.pagination import (
    CursorPosition,
    build_page,
    clamp_page_size,
    decode_cursor,
    scope_of,
)
from shaidago.shared.problems import ProblemDetails

router = APIRouter(prefix="/reviewer/reports/{report_id}/notes", tags=["reviewer"])

PROBLEMS: dict[int | str, dict[str, Any]] = {
    400: {"model": ProblemDetails, "description": "Bad body or invalid pagination cursor."},
    401: {"model": ProblemDetails},
    403: {"model": ProblemDetails},
    404: {"model": ProblemDetails},
    422: {"model": ProblemDetails},
    503: {"model": ProblemDetails},
}


class NoteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    body: Annotated[str, Field(max_length=notes.MAX_CHARS + 500)]


class NoteCreatedOut(BaseModel):
    note_id: UUID
    created_at: datetime


class NoteOut(BaseModel):
    note_id: UUID
    created_at: datetime
    author: str | None
    body: str | None


class NotePageOut(BaseModel):
    items: list[NoteOut]
    next_cursor: str | None


class NoteParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    limit: Annotated[int | None, Field(ge=1, le=1000)] = None
    cursor: Annotated[str | None, Field(max_length=512)] = None


@router.post(
    "",
    response_model=NoteCreatedOut,
    status_code=201,
    responses=PROBLEMS,
    operation_id="reviewer_notes_create",
)
async def add_note(  # noqa: PLR0913 - a route names its collaborators
    report_id: UUID,
    body: NoteRequest,
    *,
    request: Request,
    response: Response,
    reviewer: Annotated[AuthenticatedReviewer, Depends(require(Capability.NOTE_WRITE))],
    dependencies: Annotated[Dependencies, Depends(get_dependencies)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> NoteCreatedOut:
    response.headers["Cache-Control"] = "no-store"
    async with reviewer_database(dependencies).unit_of_work() as session:
        note_id, created_at = await notes.add_note(
            ReviewContext.build(session, dependencies, settings),
            actor_of(reviewer, request),
            report_id,
            body.body,
        )
    return NoteCreatedOut(note_id=note_id, created_at=created_at)


@router.get("", response_model=NotePageOut, responses=PROBLEMS, operation_id="reviewer_notes_list")
async def list_notes(  # noqa: PLR0913 - a route names its collaborators
    report_id: UUID,
    *,
    request: Request,
    response: Response,
    _: Annotated[AuthenticatedReviewer, Depends(require(Capability.REPORT_DETAIL_READ))],
    dependencies: Annotated[Dependencies, Depends(get_dependencies)],
    settings: Annotated[Settings, Depends(get_settings)],
    params: Annotated[NoteParams, Query()],
) -> NotePageOut:
    response.headers["Cache-Control"] = "no-store"
    reject_unknown_query(request, frozenset({"limit", "cursor"}))
    page_size = clamp_page_size(params.limit)
    key = settings.crypto.cursor_key()
    scope = scope_of("/v1/reviewer/reports/notes", report=str(report_id))
    after = None
    if params.cursor is not None:
        position = decode_cursor(key, scope, params.cursor)
        after = (datetime.fromisoformat(str(position.sort_value)), position.row_id)
    async with reviewer_database(dependencies).unit_of_work() as session:
        rows = await notes.list_notes(
            ReviewContext.build(session, dependencies, settings), report_id, page_size + 1, after
        )
    page = build_page(
        rows,
        page_size,
        position_of=lambda row: CursorPosition(row[1].isoformat(), row[0]),
        key=key,
        scope=scope,
    )
    return NotePageOut(
        items=[
            NoteOut(note_id=row[0], created_at=row[1], author=row[2], body=row[3])
            for row in page.items
        ],
        next_cursor=page.next_cursor,
    )
