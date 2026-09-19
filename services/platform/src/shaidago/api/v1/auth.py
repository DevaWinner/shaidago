"""Reviewer sign-in and sign-out.

Sign-in never says whether an identifier exists, the password was wrong, or the account is
disabled: all give one ``invalid_credentials`` response, and an unknown identifier still costs a
password verification. Abuse is bounded per client (attempts) and per client-and-identifier, both
keyed by the BFF's pseudonymous client HMAC, so an attacker at another address cannot lock a
reviewer out. Attempted identifiers and passwords are never stored or logged.
"""

import hashlib
from datetime import timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shaidago.api.dependencies import Dependencies, get_dependencies, get_settings
from shaidago.api.reviewer_auth import (
    AuthenticatedReviewer,
    authenticated_reviewer,
    reviewer_database,
    session_service,
)
from shaidago.audit.events import AuditWriter
from shaidago.auth.cookies import CookiePolicy
from shaidago.auth.reviewers import find_reviewer
from shaidago.auth.sessions import IssuedSession
from shaidago.shared.config import Settings
from shaidago.shared.problems import (
    DEPENDENCY_UNAVAILABLE,
    INVALID_CREDENTIALS,
    PAYLOAD_TOO_LARGE,
    RATE_LIMITED,
    ProblemDetails,
    ProblemError,
)
from shaidago.shared.ratelimit import RateDecision, RateLimitUnavailableError

router = APIRouter(prefix="/auth", tags=["auth"])

MAX_BODY_BYTES = 2048
WINDOW_SECONDS = 15 * 60
PAIR_LIMIT = 5
PROBLEMS: dict[int | str, dict[str, Any]] = {
    400: {"model": ProblemDetails, "description": "The body could not be parsed."},
    401: {"model": ProblemDetails},
    403: {"model": ProblemDetails},
    413: {"model": ProblemDetails},
    422: {"model": ProblemDetails},
    429: {"model": ProblemDetails},
    503: {"model": ProblemDetails},
}


class SignInRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    identifier: Annotated[str, Field(min_length=1, max_length=128)]
    password: Annotated[str, Field(min_length=1, max_length=256)]


class CookieOut(BaseModel):
    """What the BFF must set; the API never sets cookies itself."""

    name: str
    secure: bool
    http_only: bool
    same_site: str
    path: str
    max_age_seconds: int


class ReviewerOut(BaseModel):
    role: str


class SessionOut(BaseModel):
    """Returned once, to the trusted BFF only. Never cached, never logged."""

    session_token: str
    csrf_token: str
    expires_at: str
    idle_timeout_seconds: int
    cookie: CookieOut
    reviewer: ReviewerOut


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:32]


async def _limit(dependencies: Dependencies, key: str, limit: int) -> RateDecision:
    limiter = dependencies.rate_limiter
    if limiter is None:
        raise ProblemError(DEPENDENCY_UNAVAILABLE)
    try:
        return await limiter.hit(key, limit=limit, window_seconds=WINDOW_SECONDS)
    except RateLimitUnavailableError:
        raise ProblemError(DEPENDENCY_UNAVAILABLE) from None


async def _audit(
    session: AsyncSession,
    dependencies: Dependencies,
    request: Request,
    outcome: str,
    **kwargs: Any,
) -> None:
    await AuditWriter(session, dependencies.clock, dependencies.ids).record(
        "reviewer_sign_in",
        actor_type="reviewer",
        outcome=outcome,  # type: ignore[arg-type]  # one of success, failure, denied
        request_id=getattr(request.state, "request_id", None),
        **kwargs,
    )


def refuse_large_body(request: Request) -> None:
    """Runs before body validation. The BFF also enforces this cap while streaming."""
    declared = request.headers.get("content-length")
    if declared is not None and declared.isdigit() and int(declared) > MAX_BODY_BYTES:
        raise ProblemError(PAYLOAD_TOO_LARGE)


@router.post(
    "/sessions",
    response_model=SessionOut,
    status_code=201,
    responses=PROBLEMS,
    dependencies=[Depends(refuse_large_body)],
)
async def sign_in(
    body: SignInRequest,
    request: Request,
    response: Response,
    dependencies: Annotated[Dependencies, Depends(get_dependencies)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> SessionOut:
    response.headers["Cache-Control"] = "no-store"
    client = getattr(request.state, "client_hmac", None) or "unknown"
    per_client = settings.rate_limits.sign_in_per_15_minutes
    checks = (
        (f"sg:rl:signin:client:{client}", per_client),
        (f"sg:rl:signin:pair:{client}:{_digest(body.identifier.strip().lower())}", PAIR_LIMIT),
    )
    database = reviewer_database(dependencies)
    for key, limit in checks:
        decision = await _limit(dependencies, key, limit)
        if not decision.allowed:
            async with database.unit_of_work() as session:
                await _audit(
                    session, dependencies, request, "denied", details={"reason": "rate_limited"}
                )
            raise ProblemError(
                RATE_LIMITED, headers={"Retry-After": str(decision.retry_after_seconds)}
            )
    issued: IssuedSession | None = None
    async with database.unit_of_work() as session:
        reviewer = await find_reviewer(session, body.identifier)
        verification = dependencies.password_verifier.verify(
            reviewer.password_hash if reviewer else None, body.password
        )
        if reviewer is None or not verification.matches or reviewer.state != "active":
            await _audit(
                session, dependencies, request, "failure", details={"reason": "invalid_credentials"}
            )
        else:
            if verification.new_hash is not None:
                await session.execute(
                    text(
                        "UPDATE app.reviewers SET password_hash = :hash, "
                        "updated_at = :now WHERE id = :id"
                    ),
                    {
                        "hash": verification.new_hash,
                        "now": dependencies.clock.now(),
                        "id": reviewer.id,
                    },
                )
            await session.execute(
                text("UPDATE app.reviewers SET last_sign_in_at = :now WHERE id = :id"),
                {"now": dependencies.clock.now(), "id": reviewer.id},
            )
            issued = await session_service(session, dependencies, settings).issue(reviewer)
            await _audit(
                session, dependencies, request, "success",
                actor_id=reviewer.id, subject_type="reviewer", subject_id=reviewer.id,
            )  # fmt: skip
    if issued is None or reviewer is None:  # the failure audit event is already committed
        raise ProblemError(INVALID_CREDENTIALS)
    policy = CookiePolicy.from_settings(settings.auth)
    return SessionOut(
        session_token=issued.token,
        csrf_token=issued.csrf_token,
        expires_at=issued.absolute_expires_at.isoformat(),
        idle_timeout_seconds=int(issued.idle_timeout / timedelta(seconds=1)),
        cookie=CookieOut(
            name=policy.name,
            secure=policy.secure,
            http_only=policy.http_only,
            same_site=policy.same_site,
            path=policy.path,
            max_age_seconds=policy.max_age_seconds,
        ),
        reviewer=ReviewerOut(role=reviewer.role),
    )


@router.delete("/sessions/current", status_code=204, responses=PROBLEMS)
async def sign_out(
    reviewer: Annotated[AuthenticatedReviewer, Depends(authenticated_reviewer)],
    request: Request,
    dependencies: Annotated[Dependencies, Depends(get_dependencies)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    database = reviewer_database(dependencies)
    async with database.unit_of_work() as session:
        await session_service(session, dependencies, settings).revoke_token(reviewer.session_token)
        await AuditWriter(session, dependencies.clock, dependencies.ids).record(
            "reviewer_sign_out",
            actor_type="reviewer",
            actor_id=reviewer.principal.reviewer_id,
            subject_type="reviewer_session",
            subject_id=reviewer.principal.session_id,
            request_id=getattr(request.state, "request_id", None),
        )
    return Response(status_code=204, headers={"Cache-Control": "no-store"})
