"""Reviewer authentication for FastAPI routes.

The trusted BFF forwards the session token from its cookie in ``X-Shaidago-Session`` and, for
state-changing requests, the CSRF token in ``X-Shaidago-Csrf``. The API never reads cookies. The
internal service credential (ADR-0002) proves the caller is the BFF and nothing more: every
reviewer route additionally needs a valid session, and every failure to establish one looks the
same to the caller.
"""

from dataclasses import dataclass
from datetime import timedelta
from typing import Annotated, Final

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from shaidago.api.dependencies import Dependencies, get_dependencies, get_settings
from shaidago.auth.sessions import Principal, SessionLifetimes, SessionService, csrf_matches
from shaidago.shared.config import Settings
from shaidago.shared.database import Database
from shaidago.shared.problems import (
    CSRF_INVALID,
    DEPENDENCY_UNAVAILABLE,
    UNAUTHENTICATED,
    ProblemError,
)

SESSION_HEADER: Final = "x-shaidago-session"
CSRF_HEADER: Final = "x-shaidago-csrf"
SAFE_METHODS: Final = frozenset({"GET", "HEAD", "OPTIONS"})


@dataclass(frozen=True)
class AuthenticatedReviewer:
    principal: Principal
    session_token: str


def reviewer_database(dependencies: Dependencies) -> Database:
    database = dependencies.reviewer_database
    if database is None:
        raise ProblemError(DEPENDENCY_UNAVAILABLE)
    return database


def session_service(
    session: AsyncSession, dependencies: Dependencies, settings: Settings
) -> SessionService:
    return SessionService(
        session,
        key=settings.auth.session_key(),
        clock=dependencies.clock,
        ids=dependencies.ids,
        lifetimes=SessionLifetimes(
            idle=timedelta(minutes=settings.auth.session_idle_minutes),
            absolute=timedelta(hours=settings.auth.session_absolute_hours),
        ),
    )


async def authenticated_reviewer(
    request: Request,
    dependencies: Annotated[Dependencies, Depends(get_dependencies)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthenticatedReviewer:
    """Resolve the session, then require a matching CSRF token on state-changing methods."""
    token = request.headers.get(SESSION_HEADER)
    database = reviewer_database(dependencies)
    async with database.unit_of_work() as session:
        principal = await session_service(session, dependencies, settings).resolve(token)
    if principal is None or token is None:
        raise ProblemError(UNAUTHENTICATED)
    if request.method not in SAFE_METHODS:
        presented = request.headers.get(CSRF_HEADER, "")
        if not csrf_matches(settings.auth.session_key(), token, presented):
            raise ProblemError(CSRF_INVALID)
    return AuthenticatedReviewer(principal=principal, session_token=token)
