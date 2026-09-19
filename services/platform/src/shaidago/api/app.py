"""Application factory: no I/O happens at import time or inside ``create_app`` itself."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from importlib.metadata import version
from typing import TYPE_CHECKING

from fastapi import FastAPI

from shaidago.api import v1
from shaidago.auth.internal import InternalAuthMiddleware, InternalCallerRegistry
from shaidago.shared.context import RequestContextMiddleware
from shaidago.shared.lifecycle import open_resources

if TYPE_CHECKING:
    from shaidago.api.dependencies import Dependencies
    from shaidago.shared.config import Settings

API_TITLE = "ShaidaGo platform API"


def create_app(settings: Settings, dependencies: Dependencies) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
        async with open_resources(dependencies.resources):
            yield

    # Interactive docs exist only when configuration allows them (never in staging/production).
    # The schema itself stays generatable through ``app.openapi()`` regardless.
    docs = settings.app.docs_enabled
    app = FastAPI(
        title=API_TITLE,
        version=version("shaidago-platform"),
        lifespan=lifespan,
        docs_url="/docs" if docs else None,
        redoc_url=None,
        openapi_url="/openapi.json" if docs else None,
    )
    app.state.settings = settings
    app.state.dependencies = dependencies
    app.include_router(v1.router)
    # Middleware order is outermost-last: authentication must run before request context so
    # forwarded headers are trusted only from an authenticated caller.
    app.add_middleware(RequestContextMiddleware, new_id=dependencies.new_request_id)
    app.add_middleware(
        InternalAuthMiddleware,
        registry=InternalCallerRegistry.from_settings(settings.auth),
        new_request_id=dependencies.new_request_id,
    )
    return app
