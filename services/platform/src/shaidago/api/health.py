"""Liveness and readiness routes.

Liveness proves only that the process answers. Readiness delegates to
:func:`shaidago.shared.health.evaluate_readiness`.
"""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel

from shaidago.api.dependencies import Dependencies, get_dependencies, get_settings
from shaidago.shared.config import Settings
from shaidago.shared.health import ReadinessResponse, evaluate_readiness


class LiveResponse(BaseModel):
    status: Literal["live"]


router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live", response_model=LiveResponse)
async def live(response: Response) -> LiveResponse:
    response.headers["Cache-Control"] = "no-store"
    return LiveResponse(status="live")


@router.get("/ready", response_model=ReadinessResponse)
async def ready(
    response: Response,
    dependencies: Annotated[Dependencies, Depends(get_dependencies)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ReadinessResponse:
    report = await evaluate_readiness(
        dependencies.health_checks, settings.observability.readiness_timeout_seconds
    )
    response.headers["Cache-Control"] = "no-store"
    if report.status == "unavailable":
        response.status_code = 503
    return report
