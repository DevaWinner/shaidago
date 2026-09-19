"""Injectable collaborators for the application and FastAPI accessors for them."""

from collections.abc import Callable
from dataclasses import dataclass, field

from fastapi import Request

from shaidago.shared.config import Settings
from shaidago.shared.context import new_request_id
from shaidago.shared.health import HealthCheck
from shaidago.shared.lifecycle import ManagedResource


@dataclass(frozen=True)
class Dependencies:
    """Everything ``create_app`` may not construct itself, so tests can substitute fixtures.

    Later tasks add the clock and the shared identifier generator (BE-034), repositories, and
    provider adapters here rather than reading module globals.
    """

    resources: tuple[ManagedResource, ...] = field(default_factory=tuple)
    new_request_id: Callable[[], str] = new_request_id
    health_checks: tuple[HealthCheck, ...] = field(default_factory=tuple)


def get_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def get_dependencies(request: Request) -> Dependencies:
    dependencies: Dependencies = request.app.state.dependencies
    return dependencies
