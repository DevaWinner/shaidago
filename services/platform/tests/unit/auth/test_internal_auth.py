import hmac
from typing import TYPE_CHECKING

import pytest
from fastapi import APIRouter, Request
from fastapi.testclient import TestClient

from shaidago.auth import internal
from tests.factories import CREDENTIAL, build_settings, build_test_app

if TYPE_CHECKING:
    from fastapi import FastAPI

PREVIOUS = "previous-" + "p" * 40
CANARY_ROUTE_HIT = "route-executed"


def app_with_probe(**environ: str) -> tuple[FastAPI, list[str]]:
    app = build_test_app(build_settings(**environ))
    hits: list[str] = []
    router = APIRouter()

    @router.get("/v1/probe")
    def probe(request: Request) -> dict[str, str]:
        hits.append(CANARY_ROUTE_HIT)
        return {"caller": request.state.caller_id}

    @router.get("/health/live")
    def live() -> dict[str, str]:
        return {"status": "live"}

    app.include_router(router)
    return app, hits


def without_request_id(body: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in body.items() if key != "request_id"}


def bearer(secret: str, caller: str = "web") -> dict[str, str]:
    return {"Authorization": f"Bearer {caller}.{secret}"}


def test_valid_credential_reaches_the_route_and_identifies_the_caller() -> None:
    app, hits = app_with_probe()
    response = TestClient(app).get("/v1/probe", headers=bearer(CREDENTIAL))
    assert response.status_code == 200
    assert response.json() == {"caller": "web"}
    assert hits == [CANARY_ROUTE_HIT]


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": ""},
        {"Authorization": "Basic d2ViOnNlY3JldA=="},
        {"Authorization": "Bearer"},
        {"Authorization": "Bearer web"},
        {"Authorization": "Bearer web."},
        {"Authorization": "Bearer .secret"},
        {"Authorization": f"Bearer {CREDENTIAL}"},
        bearer("wrong-" + "w" * 40),
        bearer(CREDENTIAL, caller="worker"),
        bearer(CREDENTIAL, caller="WEB"),
        bearer(CREDENTIAL + "x"),
        bearer(CREDENTIAL[:-1]),
    ],
)
def test_missing_malformed_and_wrong_credentials_get_one_generic_denial(
    headers: dict[str, str],
) -> None:
    app, hits = app_with_probe()
    responses = TestClient(app).get("/v1/probe", headers=headers)
    baseline = TestClient(app).get("/v1/probe")
    assert responses.status_code == 401
    assert responses.headers["content-type"] == "application/problem+json"
    assert responses.headers["www-authenticate"] == "Bearer"
    assert responses.headers["cache-control"] == "no-store"
    assert without_request_id(responses.json()) == without_request_id(baseline.json())
    assert responses.json()["request_id"] == responses.headers["x-request-id"]
    assert responses.json()["code"] == "unauthenticated"
    assert hits == []


def test_previous_credential_is_accepted_only_during_rotation() -> None:
    rotating, _ = app_with_probe(INTERNAL_WEB_CREDENTIAL_PREVIOUS=PREVIOUS)
    assert TestClient(rotating).get("/v1/probe", headers=bearer(PREVIOUS)).status_code == 200
    assert TestClient(rotating).get("/v1/probe", headers=bearer(CREDENTIAL)).status_code == 200
    retired, _ = app_with_probe()
    assert TestClient(retired).get("/v1/probe", headers=bearer(PREVIOUS)).status_code == 401


def test_only_liveness_is_exempt() -> None:
    app, _ = app_with_probe()
    client = TestClient(app)
    assert client.get("/health/live").status_code == 200
    assert client.get("/health/ready").status_code == 401
    assert client.get("/v1/unknown").status_code == 401
    assert client.get("/openapi.json").status_code == 401


def test_denied_requests_never_reach_the_router_even_for_unknown_paths() -> None:
    app, _ = app_with_probe()
    # An unauthenticated caller must not learn which paths exist.
    assert TestClient(app).get("/v1/does-not-exist").status_code == 401


def test_comparison_uses_constant_time_primitive_for_known_and_unknown_callers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[bytes, bytes]] = []
    real = hmac.compare_digest

    def spy(a: bytes, b: bytes) -> bool:
        calls.append((a, b))
        return real(a, b)

    monkeypatch.setattr(internal.hmac, "compare_digest", spy)
    registry = internal.InternalCallerRegistry.from_settings(build_settings().auth)
    registry.authenticate(f"Bearer web.{CREDENTIAL}")
    registry.authenticate("Bearer nobody.guess")
    assert len(calls) == 4  # two comparisons per attempt, regardless of caller validity


def test_credential_is_never_written_to_logs_or_the_response(
    caplog: pytest.LogCaptureFixture,
) -> None:
    app, _ = app_with_probe()
    secret = "leaky-" + "s" * 40
    with caplog.at_level("DEBUG"):
        response = TestClient(app).get("/v1/probe", headers=bearer(secret))
    assert secret not in response.text
    assert secret not in caplog.text
    security = [r for r in caplog.records if r.name == "shaidago.security"]
    assert [r.__dict__.get("security_event") for r in security] == ["internal_auth_denied"]
