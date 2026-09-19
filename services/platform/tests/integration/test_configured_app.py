import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import URL

from shaidago.api.main import create_configured_app
from tests.factories import CREDENTIAL, development_environ

AUTH = {"Authorization": f"Bearer web.{CREDENTIAL}"}


def configure(monkeypatch: pytest.MonkeyPatch, url: URL) -> None:
    for name, value in development_environ().items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("DATABASE_URL", url.render_as_string(hide_password=False))
    monkeypatch.setenv("DATABASE_CONNECT_TIMEOUT_SECONDS", "1")


def test_readiness_reports_the_real_database_as_ok(
    monkeypatch: pytest.MonkeyPatch, database_url: URL
) -> None:
    configure(monkeypatch, database_url)
    with TestClient(create_configured_app(), headers=AUTH) as client:
        response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "components": {"database": "ok"}}


def test_api_starts_with_the_database_down_and_reports_unavailable(
    monkeypatch: pytest.MonkeyPatch, database_url: URL
) -> None:
    configure(monkeypatch, database_url.set(port=1))
    with TestClient(create_configured_app(), headers=AUTH) as client:
        assert client.get("/health/live").status_code == 200
        response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "unavailable", "components": {"database": "unavailable"}}
    assert "port" not in response.text
