"""Internal caller authentication (ADR-0002).

The private API never trusts network location. Every request except ``/health/live`` must carry
``Authorization: Bearer <caller-id>.<secret>``; this proves the caller is the BFF and grants no
reviewer, reporter, or tracking authority.
"""

import hmac
import logging
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING

from shaidago.shared.problems import Problem, problem_response

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Receive, Scope, Send

    from shaidago.shared.config import AuthSettings

_logger = logging.getLogger("shaidago.security")
UNAUTHENTICATED = Problem(
    status=401,
    code="unauthenticated",
    title="Authentication required",
    detail="The request could not be authenticated.",
)
_BEARER = "bearer "
EXEMPT_PATHS: frozenset[str] = frozenset({"/health/live"})
# Compared against when the claimed caller is unknown, so timing does not reveal valid caller IDs.
_DECOY_SECRET = b"\x00" * 32


@dataclass(frozen=True)
class CallerCredentials:
    current: bytes
    previous: bytes | None = None


class InternalCallerRegistry:
    """Accepted secrets per caller: the current one, plus the previous one while rotating."""

    def __init__(self, callers: Mapping[str, CallerCredentials]) -> None:
        self._callers = dict(callers)

    @classmethod
    def from_settings(cls, auth: AuthSettings) -> InternalCallerRegistry:
        previous = auth.web_credential_previous
        return cls(
            {
                "web": CallerCredentials(
                    current=auth.web_credential_current.get_secret_value().encode(),
                    previous=previous.get_secret_value().encode() if previous else None,
                )
            }
        )

    def authenticate(self, authorization: str | None) -> str | None:
        """Return the caller ID for a valid header, otherwise ``None`` (never says why)."""
        if authorization is None or not authorization.lower().startswith(_BEARER):
            return None
        caller_id, separator, secret = authorization[len(_BEARER) :].strip().partition(".")
        if not separator or not secret:
            return None
        credentials = self._callers.get(caller_id)
        presented = secret.encode()
        # Evaluate both comparisons without short-circuiting so timing does not show which matched.
        current_ok = hmac.compare_digest(
            presented, credentials.current if credentials else _DECOY_SECRET
        )
        previous = credentials.previous if credentials else None
        previous_ok = hmac.compare_digest(presented, previous or _DECOY_SECRET)
        if credentials and (current_ok or (previous is not None and previous_ok)):
            return caller_id
        return None


class InternalAuthMiddleware:
    """Pure ASGI middleware that runs before any router and answers every failure identically."""

    def __init__(self, app: ASGIApp, registry: InternalCallerRegistry) -> None:
        self._app = app
        self._registry = registry

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "lifespan":
            await self._app(scope, receive, send)
            return
        if scope["type"] != "http":
            # No WebSocket surface exists; refuse rather than pass unauthenticated traffic through.
            await send({"type": "websocket.close", "code": 1008})
            return
        if scope["path"] in EXEMPT_PATHS:
            await self._app(scope, receive, send)
            return
        headers = dict(scope["headers"])
        raw = headers.get(b"authorization")
        caller_id = self._registry.authenticate(raw.decode("latin-1") if raw else None)
        if caller_id is None:
            _logger.warning("internal caller rejected", extra={"event": "internal_auth_denied"})
            response = problem_response(UNAUTHENTICATED, headers={"WWW-Authenticate": "Bearer"})
            await response(scope, receive, send)
            return
        scope.setdefault("state", {})["caller_id"] = caller_id
        await self._app(scope, receive, send)
