"""Reviewer evidence download broker.

Authorisation and the audit record come first; only then are bytes read from private storage and
streamed with headers that force a download. No storage URL, object key, or token exists anywhere
in the response, and the same 404 answers an unknown report, an unknown file, and a file that
belongs to another report.
"""

import hashlib
from typing import Annotated, Any
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, Request, Response

from shaidago.api.dependencies import Dependencies, get_dependencies, get_settings
from shaidago.api.reviewer_auth import AuthenticatedReviewer, require, reviewer_database
from shaidago.api.v1.reviewer_reports import actor_of
from shaidago.auth.policy import Capability
from shaidago.files.rules import UploadRejectedError
from shaidago.review import evidence
from shaidago.review.context import ReviewContext
from shaidago.shared.config import Settings
from shaidago.shared.problems import (
    DEPENDENCY_UNAVAILABLE,
    NOT_FOUND,
    ProblemDetails,
    ProblemError,
)

router = APIRouter(prefix="/reviewer/reports/{report_id}/evidence", tags=["reviewer"])
_logger = structlog.get_logger("shaidago.evidence")

PROBLEMS: dict[int | str, dict[str, Any]] = {
    200: {
        "description": "The sanitised file as an attachment.",
        "content": {"application/octet-stream": {}},
    },
    401: {"model": ProblemDetails},
    403: {"model": ProblemDetails},
    404: {"model": ProblemDetails},
    422: {"model": ProblemDetails},
    503: {"model": ProblemDetails},
}


@router.get(
    "/{evidence_id}/content",
    responses=PROBLEMS,
    response_class=Response,
    operation_id="reviewer_evidence_download",
)
async def download(  # noqa: PLR0913 - a route names its collaborators
    report_id: UUID,
    evidence_id: UUID,
    *,
    request: Request,
    reviewer: Annotated[AuthenticatedReviewer, Depends(require(Capability.EVIDENCE_DOWNLOAD))],
    dependencies: Annotated[Dependencies, Depends(get_dependencies)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    actor = actor_of(reviewer, request)
    database = reviewer_database(dependencies)
    store = dependencies.evidence_store
    if store is None:
        raise ProblemError(DEPENDENCY_UNAVAILABLE)
    async with database.unit_of_work() as session:
        record = await evidence.find_evidence(session, report_id, evidence_id)
        denied = (
            "not_found"
            if record is None
            else None
            if evidence.is_servable(record)
            else "unsafe_state"
        )
        # Committed before any byte is read, and kept even if the read then fails.
        await evidence.record_download_decision(
            ReviewContext.build(session, dependencies, settings),
            actor,
            report_id,
            evidence_id,
            denied,
        )
    if record is None or denied is not None:
        raise ProblemError(NOT_FOUND)
    try:
        data = await store.get(record.object_key)
    except UploadRejectedError, KeyError:
        _logger.error("evidence object unavailable", evidence_id=str(evidence_id))
        raise ProblemError(DEPENDENCY_UNAVAILABLE) from None
    if hashlib.sha256(data).hexdigest() != record.sha256 or len(data) != record.size_bytes:
        # Never serve bytes that are not the sanitised artifact that was recorded.
        _logger.error("evidence integrity check failed", evidence_id=str(evidence_id))
        raise ProblemError(DEPENDENCY_UNAVAILABLE)
    return Response(data, media_type=record.mime_type, headers=evidence.content_headers(record))
