"""One explicit cache decision for every response.

Only the four public project reads may be cached by a shared cache, and only when they succeed (or
revalidate). Everything else is ``no-store``: authentication, reports, tracking, Q&A, reviewer
work, discovery, downloads, health, and every error. A route that forgets to say so is made
``no-store`` here, and a route that says ``public`` where it may not is corrected, so a private
response can never leave the service with a public cache header.
"""

import re
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Message, Receive, Scope, Send

NO_STORE: Final = b"no-store"
_CACHEABLE_STATUSES: Final = frozenset({200, 304})
_CACHE_HEADERS: Final = frozenset({b"cache-control", b"pragma", b"expires"})
PUBLIC_CACHEABLE_PATHS: Final = (
    re.compile(r"^/v1/localities$"),
    re.compile(r"^/v1/projects$"),
    re.compile(r"^/v1/projects/[a-z0-9-]+$"),
    re.compile(r"^/v1/projects/[a-z0-9-]+/sources/[0-9a-f-]{36}$"),
)


def may_be_publicly_cached(method: str, path: str, status: int) -> bool:
    return (
        method == "GET"
        and status in _CACHEABLE_STATUSES
        and any(pattern.fullmatch(path) for pattern in PUBLIC_CACHEABLE_PATHS)
    )


class CachePolicyMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        async def guarded(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                declared = any(name.lower() == b"cache-control" for name, _ in headers)
                if not (
                    declared
                    and may_be_publicly_cached(scope["method"], scope["path"], message["status"])
                ):
                    headers = [(n, v) for n, v in headers if n.lower() not in _CACHE_HEADERS]
                    headers.append((b"cache-control", NO_STORE))
                message = {**message, "headers": headers}
            await send(message)

        await self._app(scope, receive, guarded)
