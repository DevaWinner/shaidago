import io
import logging
from collections.abc import Iterator

import pytest
import structlog
from fastapi import APIRouter
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from shaidago.api.app import create_app
from shaidago.api.dependencies import Dependencies
from shaidago.shared.logging import configure_logging
from shaidago.shared.problems import (
    CONFLICT,
    FORBIDDEN,
    RATE_LIMITED,
    FieldError,
    ProblemError,
    problem_for_status,
)
from tests.factories import CREDENTIAL, build_settings

FIXED_ID = "018f0000-0000-7000-8000-00000000abcd"
AUTH = {"Authorization": f"Bearer web.{CREDENTIAL}"}
CANARY = "canary-submitted-value-xyz"
SECRET_IN_EXCEPTION = "postgresql://user:sql-canary-password@db/x SELECT * FROM reports"
PROBLEM_KEYS = {"type", "title", "status", "code", "detail", "request_id"}


class Payload(BaseModel):
    title: str = Field(min_length=3)
    count: int


@pytest.fixture
def stream() -> Iterator[io.StringIO]:
    buffer = io.StringIO()
    configure_logging(service="svc", environment="test", level="INFO", stream=buffer)
    yield buffer
    structlog.reset_defaults()
    logging.getLogger().handlers.clear()


@pytest.fixture
def client() -> TestClient:
    app = create_app(build_settings(), Dependencies(new_request_id=lambda: FIXED_ID))
    router = APIRouter()

    @router.post("/v1/things")
    def create(payload: Payload) -> dict[str, str]:
        return {"title": payload.title}

    @router.get("/v1/boom")
    def boom() -> None:
        raise RuntimeError(SECRET_IN_EXCEPTION)

    @router.get("/v1/conflict")
    def conflict() -> None:
        raise ProblemError(CONFLICT)

    @router.get("/v1/limited")
    def limited() -> None:
        raise ProblemError(RATE_LIMITED, headers={"Retry-After": "60"})

    @router.get("/v1/forbidden")
    def forbidden() -> None:
        raise ProblemError(FORBIDDEN, field_errors=[FieldError("role", "insufficient")])

    app.include_router(router)
    return TestClient(app, headers=AUTH, raise_server_exceptions=False)


def assert_problem(response_json: dict[str, object], code: str) -> None:
    assert set(response_json) <= PROBLEM_KEYS | {"errors"}
    assert response_json["code"] == code
    assert response_json["type"] == f"urn:shaidago:problem:{code}"
    assert response_json["request_id"] == FIXED_ID


def test_validation_errors_return_locations_and_rule_codes_but_never_values(
    client: TestClient,
) -> None:
    response = client.post("/v1/things", json={"title": CANARY[:2], "count": CANARY})
    body = response.json()
    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"
    assert_problem(body, "validation_failed")
    assert {(e["field"], e["code"]) for e in body["errors"]} == {
        ("body.title", "string_too_short"),
        ("body.count", "int_parsing"),
    }
    assert CANARY not in response.text
    assert CANARY[:2] + '"' not in response.text


def test_malformed_json_is_a_validation_problem_not_a_stack_trace(client: TestClient) -> None:
    response = client.post(
        "/v1/things",
        content=b'{"title": "' + CANARY.encode(),
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 422
    assert CANARY not in response.text


def test_unhandled_exception_is_a_generic_500_and_the_log_is_redacted(
    client: TestClient, stream: io.StringIO
) -> None:
    response = client.get("/v1/boom")
    assert response.status_code == 500
    assert response.headers["content-type"] == "application/problem+json"
    assert response.headers["x-request-id"] == FIXED_ID
    assert_problem(response.json(), "internal_error")
    for leaked in ("postgresql", "sql-canary-password", "SELECT", "Traceback", "RuntimeError"):
        assert leaked not in response.text
    logged = stream.getvalue()
    assert "unhandled exception" in logged
    assert "Traceback" in logged
    assert "sql-canary-password" not in logged


def test_domain_problems_map_to_their_status_headers_and_field_errors(client: TestClient) -> None:
    conflict = client.get("/v1/conflict")
    assert conflict.status_code == 409
    assert_problem(conflict.json(), "conflict")
    limited = client.get("/v1/limited")
    assert limited.status_code == 429
    assert limited.headers["retry-after"] == "60"
    forbidden = client.get("/v1/forbidden")
    assert forbidden.status_code == 403
    assert forbidden.json()["errors"] == [{"field": "role", "code": "insufficient"}]


def test_unknown_route_and_wrong_method_use_the_same_shape(client: TestClient) -> None:
    missing = client.get("/v1/nope")
    assert missing.status_code == 404
    assert_problem(missing.json(), "not_found")
    wrong = client.delete("/v1/things")
    assert wrong.status_code == 405
    assert wrong.headers["allow"] == "POST"
    assert_problem(wrong.json(), "method_not_allowed")


def test_every_error_is_no_store_and_carries_the_request_id_header(client: TestClient) -> None:
    for path in ("/v1/nope", "/v1/conflict", "/v1/boom"):
        response = client.get(path)
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["x-request-id"] == FIXED_ID


def test_error_code_reaches_the_access_log(client: TestClient, stream: io.StringIO) -> None:
    client.get("/v1/conflict")
    assert '"error_code": "conflict"' in stream.getvalue()


@pytest.mark.parametrize(
    ("status", "code"), [(400, "bad_request"), (418, "bad_request"), (502, "internal_error")]
)
def test_unmapped_framework_statuses_fall_back_to_generic_problems(status: int, code: str) -> None:
    assert problem_for_status(status).code == code
