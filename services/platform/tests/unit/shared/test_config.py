import base64
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from shaidago.shared.config import ConfigurationError, KeyRing, Settings, load_settings
from tests.factories import (
    CREDENTIAL,
    KEY_A,
    KEY_B,
    PLACEHOLDER_KEY,
    development_environ,
    production_environ,
)

if TYPE_CHECKING:
    from collections.abc import Mapping
CANARY = "canary-secret-value-do-not-leak"


def failure(environ: Mapping[str, str]) -> ConfigurationError:
    with pytest.raises(ConfigurationError) as raised:
        load_settings(environ)
    return raised.value


def test_valid_development_environment_loads_with_safe_defaults() -> None:
    settings = load_settings(development_environ())
    assert settings.app.environment == "development"
    assert settings.app.debug is False
    assert settings.providers.mode == "replay"
    assert settings.storage.scanner_mode == "clamd"
    assert settings.providers.qa_model == "gpt-5.6-terra"
    assert settings.auth.session_cookie_name == "sg_session"


def test_valid_production_environment_loads() -> None:
    settings = load_settings(production_environ())
    assert settings.app.is_deployed


def test_environment_must_be_a_known_value() -> None:
    environ = development_environ() | {"APP_ENV": "prod"}
    assert "APP_ENV: literal_error" in failure(environ).problems


def test_missing_required_values_are_all_reported() -> None:
    environ = development_environ()
    for name in ("DATABASE_URL", "SESSION_HMAC_KEY", "ENCRYPTION_KEKS"):
        del environ[name]
    assert {
        "DATABASE_URL: missing",
        "SESSION_HMAC_KEY: missing",
        "ENCRYPTION_KEKS: missing",
    } <= set(failure(environ).problems)


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("DATABASE_URL", "postgresql://app:p@localhost/db"),
        ("DATABASE_URL", "not a url"),
        ("DATABASE_URL", "postgresql+psycopg://app:p@localhost"),
        ("REDIS_URL", "http://localhost:6379"),
        ("OBJECT_STORE_ENDPOINT_URL", "ftp://localhost"),
        ("OBJECT_STORE_ENDPOINT_URL", "http://user:pw@localhost:9000"),
        ("SESSION_HMAC_KEY", "not-base64!"),
        ("SESSION_HMAC_KEY", base64.b64encode(b"short").decode()),
        ("ENCRYPTION_KEKS", "kek-1"),
        ("ENCRYPTION_KEKS", f"Bad Version={KEY_A}"),
        ("ENCRYPTION_KEKS", f"kek-1={KEY_A},kek-1={KEY_B}"),
        ("INTERNAL_WEB_CREDENTIAL_CURRENT", "too-short"),
        ("DISCOVERY_PUBLIC_DAILY_RUNS", "-1"),
        ("RATE_SUBMISSION_PER_HOUR", "0"),
    ],
)
def test_malformed_values_fail_fast(name: str, value: str) -> None:
    error = failure(development_environ() | {name: value})
    assert any(problem.startswith(f"{name}:") for problem in error.problems)


def test_active_key_versions_must_exist_in_their_rings() -> None:
    environ = development_environ() | {
        "ENCRYPTION_ACTIVE_KEK_VERSION": "kek-9",
        "TRACKING_ACTIVE_PEPPER_VERSION": "pepper-9",
    }
    assert set(failure(environ).problems) == {
        "ENCRYPTION_ACTIVE_KEK_VERSION: not present in ENCRYPTION_KEKS",
        "TRACKING_ACTIVE_PEPPER_VERSION: not present in TRACKING_PEPPERS",
    }


def test_retired_key_versions_are_accepted_beside_the_active_one() -> None:
    environ = development_environ() | {"ENCRYPTION_KEKS": f"kek-1={KEY_A},kek-2={KEY_B}"}
    settings = load_settings(environ | {"ENCRYPTION_ACTIVE_KEK_VERSION": "kek-2"})
    assert set(settings.crypto.kek_keys().keys) == {"kek-1", "kek-2"}


def test_host_cookie_prefix_requires_secure_in_every_environment() -> None:
    environ = development_environ() | {"SESSION_COOKIE_NAME": "__Host-sg_session"}
    assert "SESSION_COOKIE_SECURE: __Host- cookies must be Secure" in failure(environ).problems


def test_previous_internal_credential_must_differ_from_current() -> None:
    environ = development_environ() | {"INTERNAL_WEB_CREDENTIAL_PREVIOUS": CREDENTIAL}
    assert any(p.startswith("INTERNAL_WEB_CREDENTIAL_PREVIOUS") for p in failure(environ).problems)


def test_blank_optional_secrets_are_treated_as_absent() -> None:
    environ = development_environ() | {"INTERNAL_WEB_CREDENTIAL_PREVIOUS": "", "OPENAI_API_KEY": ""}
    settings = load_settings(environ)
    assert settings.auth.web_credential_previous is None
    assert settings.providers.openai_api_key is None


def test_live_provider_mode_requires_provider_keys() -> None:
    environ = development_environ() | {"PROVIDER_MODE": "live"}
    assert {"OPENAI_API_KEY: required when PROVIDER_MODE=live"} <= set(failure(environ).problems)


@pytest.mark.parametrize(
    ("override", "expected"),
    [
        ({"DEBUG": "true"}, "DEBUG: refused in staging and production"),
        ({"DOCS_ENABLED": "true"}, "DOCS_ENABLED: API docs are disabled in staging and production"),
        ({"LOG_LEVEL": "DEBUG"}, "LOG_LEVEL: DEBUG is refused in staging and production"),
        (
            {"SESSION_COOKIE_NAME": "sg_session", "SESSION_COOKIE_SECURE": "false"},
            "SESSION_COOKIE_NAME: must be __Host-sg_session",
        ),
        (
            {"SESSION_COOKIE_SECURE": "false"},
            "SESSION_COOKIE_SECURE: must be true in staging and production",
        ),
        (
            {"OBJECT_STORE_BUCKET_IS_PUBLIC": "true"},
            "OBJECT_STORE_BUCKET_IS_PUBLIC: evidence buckets must be private",
        ),
    ],
)
@pytest.mark.parametrize("app_env", ["staging", "production"])
def test_deployed_environments_refuse_unsafe_settings(
    app_env: str, override: dict[str, str], expected: str
) -> None:
    environ = production_environ() | {"APP_ENV": app_env} | override
    assert expected in failure(environ).problems


def test_production_refuses_undeployed_scanner_but_staging_allows_it() -> None:
    environ = production_environ() | {"SCANNER_MODE": "not_deployed"}
    assert "SCANNER_MODE: not_deployed is refused in production" in failure(environ).problems
    assert load_settings(environ | {"APP_ENV": "staging"}).storage.scanner_mode == "not_deployed"


def test_production_refuses_replay_providers_but_staging_allows_them() -> None:
    environ = production_environ() | {"PROVIDER_MODE": "replay"}
    assert "PROVIDER_MODE: replay is refused in production" in failure(environ).problems
    assert load_settings(environ | {"APP_ENV": "staging"}).providers.mode == "replay"


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("SESSION_HMAC_KEY", PLACEHOLDER_KEY),
        ("IDEMPOTENCY_PEPPER", PLACEHOLDER_KEY),
        ("ENCRYPTION_KEKS", f"kek-1={PLACEHOLDER_KEY}"),
        ("TRACKING_PEPPERS", f"pepper-1={PLACEHOLDER_KEY}"),
        ("INTERNAL_WEB_CREDENTIAL_CURRENT", "change-me-" + "x" * 40),
        ("OBJECT_STORE_ACCESS_KEY_ID", "change-me-access"),
    ],
)
def test_deployed_environments_refuse_placeholder_secrets(name: str, value: str) -> None:
    error = failure(production_environ() | {name: value})
    assert f"{name}: placeholder value refused in staging and production" in error.problems


def test_placeholder_secrets_are_allowed_in_development() -> None:
    assert load_settings(development_environ() | {"SESSION_HMAC_KEY": PLACEHOLDER_KEY})


def test_failures_and_repr_never_echo_secret_values() -> None:
    environ = development_environ() | {"DATABASE_URL": f"postgresql://x:{CANARY}@h/d"}
    assert CANARY not in str(failure(environ))
    settings = load_settings(development_environ())
    rendered = repr(settings) + str(settings.model_dump())
    for canary in ("dbpass-canary", "access-secret-canary", CREDENTIAL, KEY_A, KEY_B):
        assert canary not in rendered


def test_sqlalchemy_url_is_parsed_not_concatenated() -> None:
    url = load_settings(development_environ()).database.sqlalchemy_url()
    assert (url.host, url.port, url.database) == ("localhost", 5432, "shaidago")


def test_key_ring_repr_lists_versions_only() -> None:
    ring = KeyRing.parse(f"kek-1={KEY_A}")
    assert repr(ring) == "KeyRing(versions=['kek-1'])"


def test_settings_are_immutable() -> None:
    settings: Settings = load_settings(development_environ())
    with pytest.raises(ValueError, match="frozen"):
        settings.app = settings.app  # type: ignore[misc]  # proves immutability at runtime


def test_env_example_loads_in_development_and_is_refused_in_production() -> None:
    lines = (Path(__file__).parents[5] / ".env.example").read_text().splitlines()
    environ = dict(line.split("=", 1) for line in lines if line and not line.startswith("#"))
    assert load_settings(environ).app.environment == "development"
    assert failure(environ | {"APP_ENV": "production"}).problems
