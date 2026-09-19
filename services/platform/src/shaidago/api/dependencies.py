"""Injectable collaborators for the application and FastAPI accessors for them."""

from collections.abc import Callable
from dataclasses import dataclass, field

from fastapi import Request

from shaidago.auth.passwords import PasswordVerifier
from shaidago.files.pipeline import EvidencePipeline
from shaidago.files.storage import ObjectStore
from shaidago.shared.clock import Clock, SystemClock
from shaidago.shared.config import Settings
from shaidago.shared.context import new_request_id
from shaidago.shared.database import Database
from shaidago.shared.health import HealthCheck
from shaidago.shared.ids import IdGenerator, Uuid7Generator
from shaidago.shared.lifecycle import ManagedResource
from shaidago.shared.ratelimit import RateLimiter


@dataclass(frozen=True)
class Dependencies:
    """Everything ``create_app`` may not construct itself, so tests can substitute fixtures.

    Later tasks add the reviewer and worker databases, the identifier generator, and provider
    adapters here rather than reading module globals.
    """

    resources: tuple[ManagedResource, ...] = field(default_factory=tuple)
    new_request_id: Callable[[], str] = new_request_id
    health_checks: tuple[HealthCheck, ...] = field(default_factory=tuple)
    clock: Clock = field(default_factory=SystemClock)
    # Public reads connect as shaidago_public (ADR-0003); None only in tests without a database.
    public_database: Database | None = None
    # Reviewer sign-in and reviewer routes connect as shaidago_reviewer.
    reviewer_database: Database | None = None
    ids: IdGenerator = field(default_factory=Uuid7Generator)
    password_verifier: PasswordVerifier = field(default_factory=PasswordVerifier)
    rate_limiter: RateLimiter | None = None
    # None means attachments cannot be processed; reports are still accepted without them.
    evidence_pipeline: EvidencePipeline | None = None
    # Private evidence bytes for the reviewer download broker; None means downloads are unavailable.
    evidence_store: ObjectStore | None = None
    # Floor for tracking lookups so a hit and a miss take about the same time.
    lookup_minimum_seconds: float = 0.25


def get_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def get_dependencies(request: Request) -> Dependencies:
    dependencies: Dependencies = request.app.state.dependencies
    return dependencies
