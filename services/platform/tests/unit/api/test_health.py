import asyncio
import io
import json
import logging
import time
from collections.abc import Iterator
from dataclasses import dataclass

import pytest
import structlog
from fastapi.testclient import TestClient

from shaidago.api.app import create_app
from shaidago.api.dependencies import Dependencies
from shaidago.shared.health import HealthCheck
from shaidago.shared.logging import configure_logging
from tests.factories import CREDENTIAL, build_settings

AUTH = {"Authorization": f"Bearer web.{CREDENTIAL}"}
SECRET = "dsn-canary-password-do-not-leak"


@dataclass
class FakeCheck:
    name: str
    required: bool = True
    error: Exception | None = None
    delay: float = 0.0
    calls: int = 0

    async def check(self) -> None:
        self.calls += 1
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.error is not None:
            raise self.error


def client_for(*checks: HealthCheck, timeout: str = "2") -> TestClient:
    settings = build_settings(READINESS_CHECK_TIMEOUT_SECONDS=timeout)
    return TestClient(create_app(settings, Dependencies(health_checks=checks)), headers=AUTH)


@pytest.fixture
def stream() -> Iterator[io.StringIO]:
    buffer = io.StringIO()
    configure_logging(service="svc", environment="test", level="INFO", stream=buffer)
    yield buffer
    structlog.reset_defaults()
    logging.getLogger().handlers.clear()


def test_liveness_touches_no_dependency_and_needs_no_credential() -> None:
    check = FakeCheck("database", error=RuntimeError("down"))
    client = client_for(check)
    response = client.get("/health/live", headers={"Authorization": ""})
    assert response.status_code == 200
    assert response.json() == {"status": "live"}
    assert response.headers["cache-control"] == "no-store"
    assert check.calls == 0


def test_readiness_requires_the_internal_credential() -> None:
    assert client_for().get("/health/ready", headers={"Authorization": ""}).status_code == 401


def test_all_dependencies_healthy_is_ready() -> None:
    client = client_for(FakeCheck("database"), FakeCheck("redis"), FakeCheck("object_storage"))
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "components": {"database": "ok", "redis": "ok", "object_storage": "ok"},
    }
    assert response.headers["cache-control"] == "no-store"


def test_optional_provider_outage_degrades_but_does_not_make_the_api_unready() -> None:
    client = client_for(
        FakeCheck("database"),
        FakeCheck("openai", required=False, error=RuntimeError("provider down")),
        FakeCheck("search", required=False, error=TimeoutError()),
    )
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert response.json()["components"] == {
        "database": "ok",
        "openai": "unavailable",
        "search": "unavailable",
    }


def test_required_dependency_failure_is_unavailable_with_503() -> None:
    client = client_for(FakeCheck("database", error=RuntimeError("down")), FakeCheck("redis"))
    response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json()["status"] == "unavailable"
    assert response.json()["components"] == {"database": "unavailable", "redis": "ok"}


def test_a_hung_dependency_times_out_and_checks_run_concurrently() -> None:
    hung = FakeCheck("redis", delay=30)
    slow = [FakeCheck(f"c{i}", delay=0.3) for i in range(3)]
    client = client_for(hung, *slow, timeout="0.5")
    begin = time.perf_counter()
    response = client.get("/health/ready")
    elapsed = time.perf_counter() - begin
    assert response.status_code == 503
    assert response.json()["components"]["redis"] == "unavailable"
    assert all(response.json()["components"][f"c{i}"] == "ok" for i in range(3))
    assert elapsed < 1.2  # concurrent: one timeout window, not the sum of the delays


def test_public_output_and_logs_carry_no_dependency_detail(stream: io.StringIO) -> None:
    error = RuntimeError(f"postgresql://app:{SECRET}@db.internal/shaidago refused")
    client = client_for(FakeCheck("database", error=error))
    response = client.get("/health/ready")
    assert SECRET not in response.text
    assert "db.internal" not in response.text
    assert set(response.json()) == {"status", "components"}
    logged = stream.getvalue()
    assert SECRET not in logged
    warning = next(json.loads(x) for x in logged.splitlines() if "readiness check failed" in x)
    assert warning["component"] == "database"
    assert warning["error"] == "RuntimeError"


def test_no_registered_checks_is_ready() -> None:
    assert client_for().get("/health/ready").json() == {"status": "ready", "components": {}}
