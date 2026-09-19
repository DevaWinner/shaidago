"""Request context: request ID, locale, and the client pseudonym forwarded by the trusted BFF.

Forwarded headers are read only after internal caller authentication (ADR-0002), are
syntax-validated, and are replaced (request ID) or ignored (locale, client HMAC) when invalid.
"""

import re
import time
import uuid
from collections.abc import Callable
from typing import TYPE_CHECKING, Final

import structlog

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Message, Receive, Scope, Send

REQUEST_ID_HEADER: Final = "X-Request-Id"
LOCALE_HEADER: Final = b"x-shaidago-locale"
CLIENT_HMAC_HEADER: Final = b"x-shaidago-client-hmac"
LOCALES: Final[frozenset[str]] = frozenset({"en", "ha", "ig", "yo"})
DEFAULT_LOCALE: Final = "en"

_REQUEST_ID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
# HMAC-SHA-256 of the client address, lower-case hex. Never logged: the key is on the denylist.
_CLIENT_HMAC = re.compile(r"^[0-9a-f]{64}$")

_logger = structlog.get_logger("shaidago.request")


def new_request_id() -> str:
    return str(uuid.uuid7())


def is_valid_request_id(value: str) -> bool:
    return _REQUEST_ID.fullmatch(value) is not None


class RequestContextMiddleware:
    """Establishes request ID, locale, and client pseudonym, then writes one access log line.

    Installed inside authentication, so only authenticated callers can influence any of it.
    """

    def __init__(self, app: ASGIApp, new_id: Callable[[], str] = new_request_id) -> None:
        self._app = app
        self._new_id = new_id

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return
        headers = dict(scope["headers"])
        inbound = headers.get(b"x-request-id", b"").decode("latin-1")
        request_id = inbound if is_valid_request_id(inbound) else self._new_id()
        locale = headers.get(LOCALE_HEADER, b"").decode("latin-1").lower()
        client_hmac = headers.get(CLIENT_HMAC_HEADER, b"").decode("latin-1")
        state = scope.setdefault("state", {})
        state["request_id"] = request_id
        state["locale"] = locale if locale in LOCALES else DEFAULT_LOCALE
        state["client_hmac"] = client_hmac if _CLIENT_HMAC.fullmatch(client_hmac) else None

        status_code = 500
        started = time.perf_counter()

        async def send_with_request_id(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                response_headers = message.setdefault("headers", [])
                # Error handlers already set it; never send the header twice.
                if not any(name.lower() == b"x-request-id" for name, _ in response_headers):
                    response_headers.append((b"x-request-id", request_id.encode()))
            await send(message)

        structlog.contextvars.bind_contextvars(request_id=request_id)
        try:
            await self._app(scope, receive, send_with_request_id)
        finally:
            route = scope.get("route")
            _logger.info(
                "request",
                method=scope["method"],
                route=getattr(route, "path", "unmatched"),
                status=status_code,
                error_code=state.get("error_code"),
                latency_ms=round((time.perf_counter() - started) * 1000, 2),
            )
            structlog.contextvars.clear_contextvars()
