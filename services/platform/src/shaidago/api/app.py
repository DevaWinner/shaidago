"""Application factory: no I/O happens at import time or inside ``create_app`` itself."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from importlib.metadata import version
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI

from shaidago.api import health, v1
from shaidago.api.cache_policy import CachePolicyMiddleware
from shaidago.api.errors import register_exception_handlers
from shaidago.auth.internal import InternalAuthMiddleware, InternalCallerRegistry
from shaidago.shared.context import RequestContextMiddleware
from shaidago.shared.lifecycle import open_resources
from shaidago.shared.problems import declare_problem_media_type

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
    register_exception_handlers(app)
    _document_problem_media_types(app)
    app.include_router(health.router)
    app.include_router(v1.router)
    # Middleware order is outermost-last: authentication must run before request context so
    # forwarded headers are trusted only from an authenticated caller.
    app.add_middleware(CachePolicyMiddleware)  # innermost: it sees every route's response
    app.add_middleware(RequestContextMiddleware, new_id=dependencies.new_request_id)
    app.add_middleware(
        InternalAuthMiddleware,
        registry=InternalCallerRegistry.from_settings(settings.auth),
        new_request_id=dependencies.new_request_id,
    )
    return app


def _document_problem_media_types(app: FastAPI) -> None:
    default_openapi = app.openapi

    def openapi() -> dict[str, Any]:
        if app.openapi_schema is None:
            app.openapi_schema = declare_problem_media_type(default_openapi())
        return app.openapi_schema

    app.openapi = openapi  # type: ignore[method-assign]  # documented FastAPI customisation point
