from collections.abc import Iterator

import psycopg
import pytest
from alembic import command
from sqlalchemy.engine import URL

from shaidago.db.provision import PASSWORD_VARIABLES, main, provision
from shaidago.db.revision import alembic_config
from tests.integration.conftest import disposable_database

STRONG = "not-a-placeholder-password-"


@pytest.fixture
def migrated_url(admin_connection: psycopg.Connection[tuple[object, ...]]) -> Iterator[URL]:
    with disposable_database(admin_connection) as url:
        command.upgrade(alembic_config(url.render_as_string(hide_password=False)), "head")
        yield url


def environ_for(url: URL, **overrides: str) -> dict[str, str]:
    base = {"DATABASE_URL": url.render_as_string(hide_password=False)}
    base.update({variable: STRONG + role for role, variable in PASSWORD_VARIABLES.items()})
    return base | overrides


def can_log_in(url: URL, role: str, password: str) -> bool:
    try:
        with psycopg.connect(
            host=url.host,
            port=url.port,
            dbname=url.database,
            user=role,
            password=password,
            connect_timeout=3,
        ) as connection:
            return connection.execute("SELECT current_user").fetchone() == (role,)
    except psycopg.OperationalError:
        return False


def test_provision_enables_login_for_every_application_role(migrated_url: URL) -> None:
    assert not can_log_in(migrated_url, "shaidago_public", STRONG + "shaidago_public")
    assert provision(environ_for(migrated_url)) == list(PASSWORD_VARIABLES)
    for role in PASSWORD_VARIABLES:
        assert can_log_in(migrated_url, role, STRONG + role)
    assert not can_log_in(migrated_url, "shaidago_public", "wrong-password-value-here")


def test_provision_is_repeatable_and_can_rotate_passwords(migrated_url: URL) -> None:
    provision(environ_for(migrated_url))
    provision(environ_for(migrated_url, DB_PASSWORD_PUBLIC="rotated-public-password-x"))
    assert can_log_in(migrated_url, "shaidago_public", "rotated-public-password-x")
    assert not can_log_in(migrated_url, "shaidago_public", STRONG + "shaidago_public")


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"DB_PASSWORD_PUBLIC": ""}, "DB_PASSWORD_PUBLIC is not set"),
        ({"DB_PASSWORD_WORKER": "short"}, "DB_PASSWORD_WORKER: password is too short"),
        (
            {"APP_ENV": "production", "DB_PASSWORD_REVIEWER": "change-me-reviewer-password"},
            "DB_PASSWORD_REVIEWER is a placeholder",
        ),
    ],
)
def test_provision_refuses_missing_short_and_deployed_placeholder_passwords(
    migrated_url: URL, override: dict[str, str], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        provision(environ_for(migrated_url, **override))


def test_cli_reports_failure_without_echoing_secrets(
    monkeypatch: pytest.MonkeyPatch, migrated_url: URL, capsys: pytest.CaptureFixture[str]
) -> None:
    for name, value in environ_for(migrated_url, DB_PASSWORD_WORKER="tiny").items():
        monkeypatch.setenv(name, value)
    assert main() == 1
    err = capsys.readouterr().err
    assert "DB_PASSWORD_WORKER" in err
    assert "tiny" not in err
    assert STRONG not in err
