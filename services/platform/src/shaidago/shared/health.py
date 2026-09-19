"""Dependency probes and the readiness verdict, independent of HTTP.

Every registered check runs concurrently under a short timeout and is reported as ``ok`` or
``unavailable`` with no further detail, so the result is safe to return and to log.
"""

import asyncio
from dataclasses import dataclass
from typing import Literal, Protocol

import structlog
from pydantic import BaseModel

_logger = structlog.get_logger("shaidago.health")

ComponentStatus = Literal["ok", "unavailable"]


class HealthCheck(Protocol):
    """One dependency probe. ``check`` raises when the dependency is not usable."""

    name: str
    # Required checks make the API unready; optional ones (providers) only degrade it.
    required: bool

    async def check(self) -> None: ...


class ReadinessResponse(BaseModel):
    status: Literal["ready", "degraded", "unavailable"]
    components: dict[str, ComponentStatus]


@dataclass(frozen=True)
class _Outcome:
    name: str
    required: bool
    status: ComponentStatus


async def _run(check: HealthCheck, timeout_seconds: float) -> _Outcome:
    try:
        async with asyncio.timeout(timeout_seconds):
            await check.check()
    except Exception as error:
        _logger.warning("readiness check failed", component=check.name, error=type(error).__name__)
        return _Outcome(check.name, check.required, "unavailable")
    return _Outcome(check.name, check.required, "ok")


async def evaluate_readiness(
    checks: tuple[HealthCheck, ...], timeout_seconds: float
) -> ReadinessResponse:
    outcomes = await asyncio.gather(*(_run(check, timeout_seconds) for check in checks))
    failed_required = any(o.status != "ok" and o.required for o in outcomes)
    failed_optional = any(o.status != "ok" and not o.required for o in outcomes)
    status: Literal["ready", "degraded", "unavailable"] = (
        "unavailable" if failed_required else "degraded" if failed_optional else "ready"
    )
    return ReadinessResponse(status=status, components={o.name: o.status for o in outcomes})
