import io
import json
import logging
from collections.abc import Iterator

import pytest
import structlog
from fastapi import APIRouter, Request
from fastapi.testclient import TestClient

from shaidago.api.app import create_app
from shaidago.api.dependencies import Dependencies
from shaidago.shared.logging import configure_logging
from tests.factories import CREDENTIAL, build_settings

FIXED_ID = "018f0000-0000-7000-8000-00000000abcd"
INBOUND_ID = "018f1111-2222-7333-8444-555566667777"
CLIENT_HMAC = "ab" * 32
AUTH = {"Authorization": f"Bearer web.{CREDENTIAL}"}


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

    @router.get("/v1/echo/{item}")
    def echo(item: str, request: Request) -> dict[str, str | None]:
        return {
            "request_id": request.state.request_id,
            "locale": request.state.locale,
            "client_hmac": request.state.client_hmac,
            "item": item,
        }

    app.include_router(router)
    return TestClient(app, headers=AUTH)


def test_valid_inbound_request_id_is_kept_and_echoed(client: TestClient) -> None:
    response = client.get("/v1/echo/a", headers={"X-Request-Id": INBOUND_ID})
    assert response.json()["request_id"] == INBOUND_ID
    assert response.headers["x-request-id"] == INBOUND_ID


@pytest.mark.parametrize(
    "bad", ["", "not-a-uuid", INBOUND_ID.upper(), INBOUND_ID + "x", "1" * 300, "../../etc/passwd"]
)
def test_invalid_inbound_request_id_is_replaced(client: TestClient, bad: str) -> None:
    response = client.get("/v1/echo/a", headers={"X-Request-Id": bad})
    assert response.json()["request_id"] == FIXED_ID
    assert response.headers["x-request-id"] == FIXED_ID


def test_forged_context_headers_from_an_unauthenticated_caller_are_ignored(
    client: TestClient,
) -> None:
    forged = {"X-Request-Id": INBOUND_ID, "X-Shaidago-Locale": "yo"}
    response = client.get("/v1/echo/a", headers=forged | {"Authorization": "Bearer web.wrong"})
    assert response.status_code == 401
    assert response.headers["x-request-id"] == FIXED_ID
    assert response.json()["request_id"] == FIXED_ID


def test_locale_is_validated_and_defaults_to_english(client: TestClient) -> None:
    assert client.get("/v1/echo/a", headers={"X-Shaidago-Locale": "ha"}).json()["locale"] == "ha"
    assert client.get("/v1/echo/a", headers={"X-Shaidago-Locale": "IG"}).json()["locale"] == "ig"
    for bad in ("fr", "", "en-GB", "yo;q=1"):
        assert client.get("/v1/echo/a", headers={"X-Shaidago-Locale": bad}).json()["locale"] == "en"


def test_client_hmac_must_be_64_hex_characters_else_it_is_ignored(client: TestClient) -> None:
    ok = client.get("/v1/echo/a", headers={"X-Shaidago-Client-Hmac": CLIENT_HMAC})
    assert ok.json()["client_hmac"] == CLIENT_HMAC
    for bad in ("short", "zz" * 32, CLIENT_HMAC.upper(), CLIENT_HMAC + "0"):
        response = client.get("/v1/echo/a", headers={"X-Shaidago-Client-Hmac": bad})
        assert response.json()["client_hmac"] is None


def test_access_log_has_route_template_and_never_the_path_values_or_hmac(
    client: TestClient, stream: io.StringIO
) -> None:
    client.get(
        "/v1/echo/SG-7GQ2K-9M4XV-C8HTB-3WNZD-R",
        headers={"X-Request-Id": INBOUND_ID, "X-Shaidago-Client-Hmac": CLIENT_HMAC},
    )
    output = stream.getvalue()
    assert "SG-7GQ2K" not in output
    assert CLIENT_HMAC not in output
    [record] = [json.loads(line) for line in output.splitlines() if '"request"' in line]
    assert record["event"] == "request"
    assert record["route"] == "/v1/echo/{item}"
    assert record["method"] == "GET"
    assert record["status"] == 200
    assert record["request_id"] == INBOUND_ID
    assert record["latency_ms"] >= 0
    assert record["service"] == "svc"


def test_unmatched_routes_log_a_fixed_label_not_the_requested_path(
    client: TestClient, stream: io.StringIO
) -> None:
    client.get("/v1/SG-7GQ2K-9M4XV-C8HTB-3WNZD-R/leak")
    output = stream.getvalue()
    assert "SG-7GQ2K" not in output
    assert '"route": "unmatched"' in output


def test_request_id_does_not_leak_between_requests(client: TestClient, stream: io.StringIO) -> None:
    client.get("/v1/echo/a", headers={"X-Request-Id": INBOUND_ID})
    structlog.get_logger("later").info("outside a request")
    later = json.loads(stream.getvalue().splitlines()[-1])
    assert "request_id" not in later
