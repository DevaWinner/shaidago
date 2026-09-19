import os
from collections.abc import Iterator

import psycopg
import pytest
from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy.engine import URL

from shaidago.api.main import create_configured_app
from shaidago.db.revision import alembic_config
from tests.factories import CREDENTIAL, development_environ
from tests.integration.conftest import disposable_database

INFRA_NAMES = (
    "OBJECT_STORE_ENDPOINT_URL",
    "OBJECT_STORE_BUCKET",
    "OBJECT_STORE_ACCESS_KEY_ID",
    "OBJECT_STORE_SECRET_ACCESS_KEY",
)
DEPENDENCIES_OK = {"database": "ok", "redis": "ok", "object_storage": "ok", "scanner": "ok"}
AUTH = {"Authorization": f"Bearer web.{CREDENTIAL}"}


def configure(monkeypatch: pytest.MonkeyPatch, url: URL) -> None:
    infra = {name: os.environ[name] for name in INFRA_NAMES}  # read before the fixtures overwrite
    for name, value in development_environ().items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("DATABASE_URL", url.render_as_string(hide_password=False))
    monkeypatch.setenv("DATABASE_URL_PUBLIC", url.render_as_string(hide_password=False))
    monkeypatch.setenv("DATABASE_URL_REVIEWER", url.render_as_string(hide_password=False))
    monkeypatch.setenv("DATABASE_CONNECT_TIMEOUT_SECONDS", "1")
    # Point every other dependency at the Compose services so only the database varies.
    password = os.environ.get("REDIS_PASSWORD", "")
    auth = f":{password}@" if password else ""
    port = os.environ.get("INFRA_REDIS_PORT", "56379")
    monkeypatch.setenv("REDIS_URL", f"redis://{auth}127.0.0.1:{port}/0")
    monkeypatch.setenv("CLAMD_PORT", os.environ.get("INFRA_CLAMD_PORT", "53310"))
    for name, value in infra.items():
        monkeypatch.setenv(name, value)


@pytest.fixture
def migrated_url(admin_connection: psycopg.Connection[tuple[object, ...]]) -> Iterator[URL]:
    with disposable_database(admin_connection) as url:
        command.upgrade(alembic_config(url.render_as_string(hide_password=False)), "head")
        yield url


@pytest.fixture
def empty_url(admin_connection: psycopg.Connection[tuple[object, ...]]) -> Iterator[URL]:
    with disposable_database(admin_connection) as url:
        yield url


def ready(monkeypatch: pytest.MonkeyPatch, url: URL) -> tuple[int, dict[str, object]]:
    configure(monkeypatch, url)
    with TestClient(create_configured_app(), headers=AUTH) as client:
        assert client.get("/health/live").status_code == 200
        response = client.get("/health/ready")
    assert "port" not in response.text
    return response.status_code, response.json()


def test_migrated_database_is_ready(monkeypatch: pytest.MonkeyPatch, migrated_url: URL) -> None:
    status, body = ready(monkeypatch, migrated_url)
    assert status == 200
    assert body == {"status": "ready", "components": {**DEPENDENCIES_OK, "migrations": "ok"}}


def test_unmigrated_database_is_unavailable_because_the_revision_is_missing(
    monkeypatch: pytest.MonkeyPatch, empty_url: URL
) -> None:
    status, body = ready(monkeypatch, empty_url)
    assert status == 503
    assert body["components"] == {**DEPENDENCIES_OK, "migrations": "unavailable"}


def test_api_starts_with_the_database_down_and_reports_unavailable(
    monkeypatch: pytest.MonkeyPatch, empty_url: URL
) -> None:
    status, body = ready(monkeypatch, empty_url.set(port=1))
    assert status == 503
    assert body == {
        "status": "unavailable",
        "components": {**DEPENDENCIES_OK, "database": "unavailable", "migrations": "unavailable"},
    }
