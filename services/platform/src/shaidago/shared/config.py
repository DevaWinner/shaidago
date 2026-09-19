"""Typed, fail-fast environment configuration.

Sections are plain frozen models validated from an explicit mapping (normally ``os.environ``),
so nothing is read at import time and tests inject their own environment. Secrets are
``SecretStr``. A failed load raises :class:`ConfigurationError`, which names variables and
failure kinds but never echoes an input value.
"""

import base64
import binascii
import re
from collections.abc import Mapping
from typing import Annotated, Literal, Self
from urllib.parse import urlsplit

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PositiveFloat,
    PositiveInt,
    SecretStr,
    ValidationError,
    field_validator,
)
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError

Environment = Literal["development", "test", "staging", "production"]
ProviderMode = Literal["live", "replay"]
ScannerMode = Literal["clamd", "not_deployed"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR"]

DEPLOYED_ENVIRONMENTS: frozenset[str] = frozenset({"staging", "production"})
PRODUCTION_COOKIE_NAME = "__Host-sg_session"
KEY_BYTES = 32
MIN_CREDENTIAL_CHARS = 32
# Example files ship key material that decodes to this prefix; deployed environments refuse it.
PLACEHOLDER_PREFIX = "change-me"

_KEY_VERSION = re.compile(r"^[a-z0-9][a-z0-9._-]{0,31}$")


class ConfigurationError(Exception):
    """Configuration is invalid. Messages carry variable names and reasons, never values."""

    def __init__(self, problems: list[str]) -> None:
        self.problems = tuple(problems)
        super().__init__("invalid configuration: " + "; ".join(self.problems))


class KeyRing(BaseModel):
    """Versioned 256-bit keys parsed from ``version=base64,version=base64``."""

    model_config = ConfigDict(frozen=True)

    keys: Mapping[str, bytes]

    def __repr__(self) -> str:
        return f"KeyRing(versions={sorted(self.keys)})"

    @classmethod
    def parse(cls, raw: str) -> Self:
        keys: dict[str, bytes] = {}
        for item in raw.split(","):
            version, separator, encoded = item.strip().partition("=")
            if not separator or not _KEY_VERSION.fullmatch(version):
                raise ValueError("entries must look like version=base64key")
            if version in keys:
                raise ValueError("duplicate key version")
            try:
                material = base64.b64decode(encoded, validate=True)
            except (binascii.Error, ValueError) as error:
                raise ValueError("key is not valid base64") from error
            if len(material) != KEY_BYTES:
                raise ValueError("key must decode to 32 bytes")
            keys[version] = material
        return cls(keys=keys)


def _secret_is_placeholder(value: str) -> bool:
    if PLACEHOLDER_PREFIX in value:
        return True
    # A bare key, or the base64 after each "version=" in a key ring.
    candidates = [value, *(part.partition("=")[2] for part in value.split(","))]
    for candidate in candidates:
        try:
            if base64.b64decode(candidate, validate=True).startswith(PLACEHOLDER_PREFIX.encode()):
                return True
        except binascii.Error, ValueError:
            continue
    return False


class _Section(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore", str_strip_whitespace=True)


class AppSettings(_Section):
    environment: Environment = Field(validation_alias="APP_ENV")
    service_name: str = Field(default="shaidago-platform", validation_alias="SERVICE_NAME")
    debug: bool = Field(default=False, validation_alias="DEBUG")
    docs_enabled: bool = Field(default=False, validation_alias="DOCS_ENABLED")

    @property
    def is_deployed(self) -> bool:
        return self.environment in DEPLOYED_ENVIRONMENTS


def _validate_database_url(value: SecretStr) -> SecretStr:
    try:
        parsed = make_url(value.get_secret_value())
    except ArgumentError as error:
        raise ValueError("not a valid database URL") from error
    if parsed.drivername != "postgresql+psycopg":
        raise ValueError("driver must be postgresql+psycopg")
    if not parsed.host or not parsed.database:
        raise ValueError("host and database name are required")
    return value


class DatabaseSettings(_Section):
    """``url`` is the migration owner (tools only); the API connects as the role URLs (ADR-0003)."""

    url: SecretStr = Field(validation_alias="DATABASE_URL")
    public_url: SecretStr = Field(validation_alias="DATABASE_URL_PUBLIC")
    pool_size: PositiveInt = Field(default=5, le=50, validation_alias="DATABASE_POOL_SIZE")
    connect_timeout_seconds: PositiveInt = Field(
        default=5, le=60, validation_alias="DATABASE_CONNECT_TIMEOUT_SECONDS"
    )
    statement_timeout_ms: PositiveInt = Field(
        default=5000, le=60_000, validation_alias="DATABASE_STATEMENT_TIMEOUT_MS"
    )

    @field_validator("url", "public_url")
    @classmethod
    def _parse_url(cls, value: SecretStr) -> SecretStr:
        return _validate_database_url(value)

    def sqlalchemy_url(self) -> URL:
        return make_url(self.url.get_secret_value())

    def public_sqlalchemy_url(self) -> URL:
        return make_url(self.public_url.get_secret_value())


class RedisSettings(_Section):
    url: SecretStr = Field(validation_alias="REDIS_URL")

    @field_validator("url")
    @classmethod
    def _check_url(cls, value: SecretStr) -> SecretStr:
        parts = urlsplit(value.get_secret_value())
        if parts.scheme not in {"redis", "rediss"} or not parts.hostname:
            raise ValueError("must be a redis:// or rediss:// URL with a host")
        return value


class StorageSettings(_Section):
    endpoint_url: str = Field(validation_alias="OBJECT_STORE_ENDPOINT_URL")
    bucket: str = Field(min_length=3, max_length=63, validation_alias="OBJECT_STORE_BUCKET")
    access_key_id: SecretStr = Field(validation_alias="OBJECT_STORE_ACCESS_KEY_ID")
    secret_access_key: SecretStr = Field(validation_alias="OBJECT_STORE_SECRET_ACCESS_KEY")
    bucket_is_public: bool = Field(default=False, validation_alias="OBJECT_STORE_BUCKET_IS_PUBLIC")
    scanner_mode: ScannerMode = Field(default="clamd", validation_alias="SCANNER_MODE")

    @field_validator("endpoint_url")
    @classmethod
    def _check_endpoint(cls, value: str) -> str:
        parts = urlsplit(value)
        if parts.scheme not in {"http", "https"} or not parts.hostname:
            raise ValueError("must be an http(s) URL with a host")
        if parts.username or parts.password:
            raise ValueError("must not embed credentials")
        return value


class CryptoSettings(_Section):
    """Envelope-encryption key ring (ADR-0004) and HMAC peppers (ADR-0005)."""

    kek_ring: SecretStr = Field(validation_alias="ENCRYPTION_KEKS")
    active_kek_version: str = Field(validation_alias="ENCRYPTION_ACTIVE_KEK_VERSION")
    tracking_pepper_ring: SecretStr = Field(validation_alias="TRACKING_PEPPERS")
    active_tracking_pepper_version: str = Field(validation_alias="TRACKING_ACTIVE_PEPPER_VERSION")
    idempotency_pepper: SecretStr = Field(validation_alias="IDEMPOTENCY_PEPPER")
    cursor_hmac_key: SecretStr = Field(validation_alias="CURSOR_HMAC_KEY")

    @field_validator("kek_ring", "tracking_pepper_ring")
    @classmethod
    def _check_key_ring(cls, value: SecretStr) -> SecretStr:
        KeyRing.parse(value.get_secret_value())
        return value

    @field_validator("idempotency_pepper", "cursor_hmac_key")
    @classmethod
    def _check_pepper(cls, value: SecretStr) -> SecretStr:
        _decode_single_key(value.get_secret_value())
        return value

    def cursor_key(self) -> bytes:
        return _decode_single_key(self.cursor_hmac_key.get_secret_value())

    def kek_keys(self) -> KeyRing:
        return KeyRing.parse(self.kek_ring.get_secret_value())

    def tracking_pepper_keys(self) -> KeyRing:
        return KeyRing.parse(self.tracking_pepper_ring.get_secret_value())


def _decode_single_key(raw: str) -> bytes:
    try:
        material = base64.b64decode(raw, validate=True)
    except (binascii.Error, ValueError) as error:
        raise ValueError("key is not valid base64") from error
    if len(material) != KEY_BYTES:
        raise ValueError("key must decode to 32 bytes")
    return material


class AuthSettings(_Section):
    """Internal caller credentials (ADR-0002) and reviewer session cookie contract."""

    web_credential_current: SecretStr = Field(
        min_length=MIN_CREDENTIAL_CHARS, validation_alias="INTERNAL_WEB_CREDENTIAL_CURRENT"
    )
    web_credential_previous: SecretStr | None = Field(
        default=None,
        min_length=MIN_CREDENTIAL_CHARS,
        validation_alias="INTERNAL_WEB_CREDENTIAL_PREVIOUS",
    )
    session_hmac_key: SecretStr = Field(validation_alias="SESSION_HMAC_KEY")
    session_cookie_name: str = Field(default="sg_session", validation_alias="SESSION_COOKIE_NAME")
    session_cookie_secure: bool = Field(default=False, validation_alias="SESSION_COOKIE_SECURE")
    session_idle_minutes: PositiveInt = Field(
        default=30, le=1440, validation_alias="SESSION_IDLE_MINUTES"
    )
    session_absolute_hours: PositiveInt = Field(
        default=8, le=72, validation_alias="SESSION_ABSOLUTE_HOURS"
    )

    def session_key(self) -> bytes:
        return _decode_single_key(self.session_hmac_key.get_secret_value())

    @field_validator("web_credential_previous", mode="before")
    @classmethod
    def _blank_previous_is_absent(cls, value: object) -> object:
        return None if value == "" else value

    @field_validator("session_hmac_key")
    @classmethod
    def _check_session_key(cls, value: SecretStr) -> SecretStr:
        _decode_single_key(value.get_secret_value())
        return value


class ProviderSettings(_Section):
    mode: ProviderMode = Field(default="replay", validation_alias="PROVIDER_MODE")
    openai_api_key: SecretStr | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    search_api_key: SecretStr | None = Field(default=None, validation_alias="SEARCH_API_KEY")
    qa_model: str = Field(default="gpt-5.6-terra", min_length=1, validation_alias="OPENAI_QA_MODEL")
    discovery_model: str = Field(
        default="gpt-6-astra", min_length=1, validation_alias="OPENAI_DISCOVERY_MODEL"
    )
    embedding_model: str = Field(
        default="text-embedding-3-small", min_length=1, validation_alias="OPENAI_EMBEDDING_MODEL"
    )
    discovery_public_daily_runs: Annotated[int, Field(ge=0, le=1000)] = Field(
        default=20, validation_alias="DISCOVERY_PUBLIC_DAILY_RUNS"
    )

    @field_validator("openai_api_key", "search_api_key", mode="before")
    @classmethod
    def _blank_key_is_absent(cls, value: object) -> object:
        return None if value == "" else value


class RateLimitSettings(_Section):
    """Requests allowed per window and per pseudonymous client. Values are reviewable defaults."""

    sign_in_per_15_minutes: PositiveInt = Field(default=10, validation_alias="RATE_SIGN_IN_PER_15M")
    submission_per_hour: PositiveInt = Field(
        default=10, validation_alias="RATE_SUBMISSION_PER_HOUR"
    )
    tracking_lookup_per_hour: PositiveInt = Field(
        default=20, validation_alias="RATE_TRACKING_LOOKUP_PER_HOUR"
    )
    handle_verify_per_hour: PositiveInt = Field(
        default=10, validation_alias="RATE_HANDLE_VERIFY_PER_HOUR"
    )
    qa_per_hour: PositiveInt = Field(default=30, validation_alias="RATE_QA_PER_HOUR")
    discovery_per_hour: PositiveInt = Field(default=5, validation_alias="RATE_DISCOVERY_PER_HOUR")


class ObservabilitySettings(_Section):
    log_level: LogLevel = Field(default="INFO", validation_alias="LOG_LEVEL")
    readiness_timeout_seconds: PositiveFloat = Field(
        default=2.0, le=10.0, validation_alias="READINESS_CHECK_TIMEOUT_SECONDS"
    )


class Settings(_Section):
    app: AppSettings
    database: DatabaseSettings
    redis: RedisSettings
    storage: StorageSettings
    crypto: CryptoSettings
    auth: AuthSettings
    providers: ProviderSettings
    rate_limits: RateLimitSettings
    observability: ObservabilitySettings


_SECTIONS: dict[str, type[_Section]] = {
    "app": AppSettings,
    "database": DatabaseSettings,
    "redis": RedisSettings,
    "storage": StorageSettings,
    "crypto": CryptoSettings,
    "auth": AuthSettings,
    "providers": ProviderSettings,
    "rate_limits": RateLimitSettings,
    "observability": ObservabilitySettings,
}


def load_settings(environ: Mapping[str, str]) -> Settings:
    """Validate ``environ`` into :class:`Settings` or raise :class:`ConfigurationError`."""
    sections: dict[str, _Section] = {}
    problems: list[str] = []
    for name, model in _SECTIONS.items():
        try:
            sections[name] = model.model_validate(environ)
        except ValidationError as error:
            for detail in error.errors(
                include_input=False, include_url=False, include_context=False
            ):
                variable = str(detail["loc"][0]) if detail["loc"] else name
                problems.append(f"{variable}: {detail['type']}")
    if problems:
        raise ConfigurationError(problems)
    settings = Settings.model_validate(sections, from_attributes=True)
    problems = _deployment_problems(settings)
    if problems:
        raise ConfigurationError(problems)
    return settings


def _secret_values(settings: Settings) -> dict[str, str]:
    optional = {
        "INTERNAL_WEB_CREDENTIAL_PREVIOUS": settings.auth.web_credential_previous,
        "OPENAI_API_KEY": settings.providers.openai_api_key,
        "SEARCH_API_KEY": settings.providers.search_api_key,
    }
    values = {
        "DATABASE_URL": settings.database.url,
        "DATABASE_URL_PUBLIC": settings.database.public_url,
        "REDIS_URL": settings.redis.url,
        "OBJECT_STORE_ACCESS_KEY_ID": settings.storage.access_key_id,
        "OBJECT_STORE_SECRET_ACCESS_KEY": settings.storage.secret_access_key,
        "ENCRYPTION_KEKS": settings.crypto.kek_ring,
        "TRACKING_PEPPERS": settings.crypto.tracking_pepper_ring,
        "IDEMPOTENCY_PEPPER": settings.crypto.idempotency_pepper,
        "CURSOR_HMAC_KEY": settings.crypto.cursor_hmac_key,
        "INTERNAL_WEB_CREDENTIAL_CURRENT": settings.auth.web_credential_current,
        "SESSION_HMAC_KEY": settings.auth.session_hmac_key,
    }
    values.update({name: secret for name, secret in optional.items() if secret is not None})
    return {name: secret.get_secret_value() for name, secret in values.items()}


def _consistency_problems(settings: Settings) -> list[str]:
    """Rules that hold in every environment."""
    problems: list[str] = []
    if settings.crypto.active_kek_version not in settings.crypto.kek_keys().keys:
        problems.append("ENCRYPTION_ACTIVE_KEK_VERSION: not present in ENCRYPTION_KEKS")
    if (
        settings.crypto.active_tracking_pepper_version
        not in settings.crypto.tracking_pepper_keys().keys
    ):
        problems.append("TRACKING_ACTIVE_PEPPER_VERSION: not present in TRACKING_PEPPERS")
    auth = settings.auth
    if auth.session_cookie_name.startswith("__Host-") and not auth.session_cookie_secure:
        problems.append("SESSION_COOKIE_SECURE: __Host- cookies must be Secure")
    previous = auth.web_credential_previous
    if (
        previous is not None
        and previous.get_secret_value() == auth.web_credential_current.get_secret_value()
    ):
        problems.append("INTERNAL_WEB_CREDENTIAL_PREVIOUS: must differ from the current credential")
    providers = settings.providers
    if providers.mode == "live":
        if providers.openai_api_key is None:
            problems.append("OPENAI_API_KEY: required when PROVIDER_MODE=live")
        if providers.search_api_key is None:
            problems.append("SEARCH_API_KEY: required when PROVIDER_MODE=live")
    return problems


def _deployment_problems(settings: Settings) -> list[str]:
    problems = _consistency_problems(settings)
    app = settings.app
    if not app.is_deployed:
        return problems
    if app.debug:
        problems.append("DEBUG: refused in staging and production")
    if app.docs_enabled:
        problems.append("DOCS_ENABLED: API docs are disabled in staging and production")
    if settings.observability.log_level == "DEBUG":
        problems.append("LOG_LEVEL: DEBUG is refused in staging and production")
    if settings.auth.session_cookie_name != PRODUCTION_COOKIE_NAME:
        problems.append(f"SESSION_COOKIE_NAME: must be {PRODUCTION_COOKIE_NAME}")
    if not settings.auth.session_cookie_secure:
        problems.append("SESSION_COOKIE_SECURE: must be true in staging and production")
    if settings.storage.bucket_is_public:
        problems.append("OBJECT_STORE_BUCKET_IS_PUBLIC: evidence buckets must be private")
    owner_user = settings.database.sqlalchemy_url().username
    if settings.database.public_sqlalchemy_url().username == owner_user:
        problems.append("DATABASE_URL_PUBLIC: must use a different login than DATABASE_URL")
    problems.extend(
        f"{name}: placeholder value refused in staging and production"
        for name, value in _secret_values(settings).items()
        if _secret_is_placeholder(value)
    )
    if app.environment == "production":
        if settings.storage.scanner_mode == "not_deployed":
            problems.append("SCANNER_MODE: not_deployed is refused in production")
        if settings.providers.mode == "replay":
            problems.append("PROVIDER_MODE: replay is refused in production")
    return problems
