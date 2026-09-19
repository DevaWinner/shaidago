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
from shaidago.reports.status_lookup import code_prefix, find_report
from shaidago.shared.config import Settings
from shaidago.shared.problems import (
    DEPENDENCY_UNAVAILABLE,
    PAYLOAD_TOO_LARGE,
    RATE_LIMITED,
    TRACKING_NOT_RECOGNISED,
    ProblemDetails,
    ProblemError,
)
from shaidago.shared.ratelimit import RateLimitUnavailableError

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
    """Reviewer questions the reporter may answer. Populated by the follow-up task (BE-067)."""

    model_config = ConfigDict(extra="forbid")

    question_id: str
    text: str


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


async def _limit(dependencies: Dependencies, key: str, limit: int) -> None:
    limiter = dependencies.rate_limiter
    if limiter is None:
        raise ProblemError(DEPENDENCY_UNAVAILABLE)
    try:
        decision = await limiter.hit(key, limit=limit, window_seconds=WINDOW_SECONDS)
    except RateLimitUnavailableError:
        raise ProblemError(DEPENDENCY_UNAVAILABLE) from None
    if not decision.allowed:
        raise ProblemError(RATE_LIMITED, headers={"Retry-After": str(decision.retry_after_seconds)})


def _bucket(client: str, prefix: str) -> str:
    return hashlib.sha256(f"{client}:{prefix}".encode()).hexdigest()[:32]


@router.post(
    "/report-status:lookup",
    response_model=ReportStatusOut,
    responses=PROBLEMS,
    dependencies=[Depends(_refuse_large_body)],
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
    await _limit(
        dependencies, f"sg:rl:track:{client}", settings.rate_limits.tracking_lookup_per_hour
    )
    prefix = code_prefix(body.code)
    if prefix is not None:
        await _limit(dependencies, f"sg:rl:track:{_bucket(client, prefix)}", PREFIX_LIMIT)
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
        follow_up_questions=[],
    )
