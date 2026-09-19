"""Tracking-code status lookup.

The code travels in the POST body only, is never echoed, and every failure (malformed, unknown,
or unreachable) is the same ``tracking_code_not_recognised`` problem. Attempts are limited per
client and per client and code prefix, and each call takes at least a fixed minimum time.
"""

import asyncio
import hashlib
import time
from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from shaidago.api.dependencies import Dependencies, get_dependencies, get_settings
from shaidago.api.rate_limits import enforce_rate_limit
from shaidago.reports.status_lookup import code_prefix, find_report
from shaidago.shared.config import Settings
from shaidago.shared.problems import (
    DEPENDENCY_UNAVAILABLE,
    PAYLOAD_TOO_LARGE,
    TRACKING_NOT_RECOGNISED,
    ProblemDetails,
    ProblemError,
)

router = APIRouter(tags=["reports"])

MAX_BODY_BYTES = 1024
WINDOW_SECONDS = 3600
PREFIX_LIMIT = 5
PROBLEMS: dict[int | str, dict[str, Any]] = {
    400: {"model": ProblemDetails, "description": "The body could not be parsed."},
    404: {"model": ProblemDetails, "description": "One answer for every unrecognised code."},
    413: {"model": ProblemDetails},
    422: {"model": ProblemDetails},
    429: {"model": ProblemDetails},
    503: {"model": ProblemDetails},
}
NextAction = Literal[
    "wait_for_review",
    "answer_follow_up",
    "watch_public_updates",
    "see_escalation_guidance",
    "none",
]


class StatusLookupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Length is not validated here on purpose: a wrong-length code is just "not recognised".
    code: Annotated[str, Field(max_length=256)]


class FollowUpQuestion(BaseModel):
    """A reviewer's question with its acknowledgement state. Answers are never returned."""

    model_config = ConfigDict(extra="forbid")

    question_id: str
    text: str
    state: Literal["open", "answered", "skipped", "unsafe"]


class ReportStatusOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal[
        "received",
        "needs_information",
        "under_review",
        "verified_for_public_update",
        "referred",
        "closed",
    ]
    status_updated_at: datetime
    message: str
    next_action: NextAction
    follow_up_questions: list[FollowUpQuestion]


def _refuse_large_body(request: Request) -> None:
    declared = request.headers.get("content-length")
    if declared is not None and declared.isdigit() and int(declared) > MAX_BODY_BYTES:
        raise ProblemError(PAYLOAD_TOO_LARGE)


def code_bucket(client: str, prefix: str) -> str:
    return hashlib.sha256(f"{client}:{prefix}".encode()).hexdigest()[:32]


@router.post(
    "/report-status:lookup",
    response_model=ReportStatusOut,
    responses=PROBLEMS,
    dependencies=[Depends(_refuse_large_body)],
    operation_id="report_status_lookup",
)
async def look_up_report_status(
    body: StatusLookupRequest,
    request: Request,
    response: Response,
    dependencies: Annotated[Dependencies, Depends(get_dependencies)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ReportStatusOut:
    response.headers["Cache-Control"] = "no-store"
    started = time.monotonic()
    client = getattr(request.state, "client_hmac", None) or "unknown"
    await enforce_rate_limit(
        dependencies,
        f"sg:rl:track:{client}",
        limit=settings.rate_limits.tracking_lookup_per_hour,
    )
    prefix = code_prefix(body.code)
    if prefix is not None:
        await enforce_rate_limit(
            dependencies, f"sg:rl:track:{code_bucket(client, prefix)}", limit=PREFIX_LIMIT
        )
    database = dependencies.public_database
    if database is None:
        raise ProblemError(DEPENDENCY_UNAVAILABLE)
    crypto = settings.crypto
    async with database.unit_of_work() as session:
        found = await find_report(
            session,
            body.code,
            dict(crypto.tracking_pepper_keys().keys),
            crypto.active_tracking_pepper_version,
        )
    remaining = dependencies.lookup_minimum_seconds - (time.monotonic() - started)
    if remaining > 0:
        await asyncio.sleep(remaining)
    if found is None:
        raise ProblemError(TRACKING_NOT_RECOGNISED)
    return ReportStatusOut(
        status=found.status,  # type: ignore[arg-type]  # checked against NEXT_ACTIONS in find_report
        status_updated_at=found.status_updated_at,
        message=found.message,
        next_action=found.next_action,  # type: ignore[arg-type]  # values of NEXT_ACTIONS
        follow_up_questions=[
            FollowUpQuestion(
                question_id=q.question_id,
                text=q.text,
                state=q.state,  # type: ignore[arg-type]  # constrained by the SQL CASE
            )
            for q in found.questions
        ],
    )
