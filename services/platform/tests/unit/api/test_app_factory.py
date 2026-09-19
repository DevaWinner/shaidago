import sys
from typing import TYPE_CHECKING

from fastapi.testclient import TestClient

from shaidago.api.dependencies import Dependencies
from shaidago.api.main import create_configured_app
from tests.factories import CREDENTIAL, build_settings, build_test_app, development_environ
from tests.unit.shared.test_lifecycle import Recorder

if TYPE_CHECKING:
    import pytest

AUTH = {"Authorization": f"Bearer web.{CREDENTIAL}"}


def test_importing_the_factory_does_no_io_and_builds_no_app() -> None:
    assert "shaidago.api.main" in sys.modules
    assert not hasattr(sys.modules["shaidago.api.main"], "app")


def test_lifespan_opens_resources_on_start_and_closes_them_on_stop() -> None:
    log: list[str] = []
    dependencies = Dependencies(resources=(Recorder("db", log), Recorder("redis", log)))
    with TestClient(build_test_app(dependencies=dependencies)):
        assert log == ["open:db", "open:redis"]
    assert log == ["open:db", "open:redis", "close:redis", "close:db"]


def test_docs_are_available_when_configuration_enables_them() -> None:
    client = TestClient(build_test_app(build_settings(DOCS_ENABLED="true")), headers=AUTH)
    assert client.get("/openapi.json").status_code == 200
    assert client.get("/docs").status_code == 200


def test_docs_routes_are_absent_when_disabled_but_the_schema_still_generates() -> None:
    app = build_test_app(build_settings(DOCS_ENABLED="false"))
    client = TestClient(app, headers=AUTH)
    assert client.get("/openapi.json").status_code == 404
    assert client.get("/docs").status_code == 404
    assert app.openapi()["info"]["title"] == "ShaidaGo platform API"


def test_schema_generation_is_deterministic_and_needs_no_running_dependencies() -> None:
    first = build_test_app().openapi()
    second = build_test_app().openapi()
    assert first == second


def test_configured_entry_point_reads_the_process_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name, value in development_environ().items():
        monkeypatch.setenv(name, value)
    assert create_configured_app().state.settings.app.environment == "development"
