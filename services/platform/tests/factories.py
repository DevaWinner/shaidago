"""Test-only builders. Overrides are keyword arguments so tests state what they change."""

import base64

from fastapi import FastAPI

from shaidago.api.app import create_app
from shaidago.api.dependencies import Dependencies
from shaidago.shared.config import Settings, load_settings

# Synthetic test-only key material; none of it protects anything.
KEY_A = base64.b64encode(b"a" * 32).decode()
KEY_B = base64.b64encode(b"b" * 32).decode()
PLACEHOLDER_KEY = base64.b64encode(b"change-me-".ljust(32, b"x")).decode()
CREDENTIAL = "credential-" + "c" * 40


def development_environ() -> dict[str, str]:
    return {
        "APP_ENV": "development",
        "DATABASE_URL": "postgresql+psycopg://app:dbpass-canary@localhost:5432/shaidago",
        "DATABASE_URL_PUBLIC": "postgresql+psycopg://shaidago_public:public-canary@localhost:5432/shaidago",
        "DATABASE_URL_REVIEWER": "postgresql+psycopg://shaidago_reviewer:reviewer-canary@localhost:5432/shaidago",
        "REDIS_URL": "redis://localhost:6379/0",
        "OBJECT_STORE_ENDPOINT_URL": "http://localhost:9000",
        "OBJECT_STORE_BUCKET": "evidence-dev",
        "OBJECT_STORE_ACCESS_KEY_ID": "access-id-canary",
        "OBJECT_STORE_SECRET_ACCESS_KEY": "access-secret-canary",
        "ENCRYPTION_KEKS": f"kek-1={KEY_A}",
        "ENCRYPTION_ACTIVE_KEK_VERSION": "kek-1",
        "TRACKING_PEPPERS": f"pepper-1={KEY_B}",
        "TRACKING_ACTIVE_PEPPER_VERSION": "pepper-1",
        "IDEMPOTENCY_PEPPER": KEY_B,
        "CURSOR_HMAC_KEY": KEY_A,
        "INTERNAL_WEB_CREDENTIAL_CURRENT": CREDENTIAL,
        "SESSION_HMAC_KEY": KEY_A,
    }


def production_environ() -> dict[str, str]:
    environ = development_environ()
    environ.update(
        {
            "APP_ENV": "production",
            "SESSION_COOKIE_NAME": "__Host-sg_session",
            "SESSION_COOKIE_SECURE": "true",
            "PROVIDER_MODE": "live",
            "OPENAI_API_KEY": "openai-live-key-canary",
            "SEARCH_API_KEY": "search-live-key-canary",
        }
    )
    return environ


def build_settings(**environ_overrides: str) -> Settings:
    return load_settings(development_environ() | environ_overrides)


def build_test_app(
    settings: Settings | None = None, dependencies: Dependencies | None = None
) -> FastAPI:
    return create_app(settings or build_settings(), dependencies or Dependencies())
