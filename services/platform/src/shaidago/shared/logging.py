"""Structured JSON logging with one central redactor.

Every log line, including stdlib and third-party records and rendered exception text, passes
through :func:`redact`. Redaction is by key (exact names and suffixes) and by value pattern, so a
sensitive value is removed even when a developer logs it under an innocent key.
"""

import ipaddress
import logging
import re
import sys
from collections.abc import Iterable, Mapping, MutableMapping
from datetime import UTC, datetime
from typing import Any, Final, TextIO, cast

import structlog
from structlog.typing import EventDict, Processor

REDACTED: Final = "[REDACTED]"

# Normalised (lower case, "-" -> "_") key names whose values are never logged.
SENSITIVE_KEYS: Final[frozenset[str]] = frozenset(
    {
        "password", "passphrase", "passwd", "secret", "token", "credential", "credentials",
        "api_key", "apikey", "authorization", "cookie", "set_cookie", "session", "session_id",
        "csrf", "csrf_token", "contact", "contacts", "email", "phone", "phone_number",
        "report", "report_text", "report_body", "body", "text", "description", "narrative",
        "answer", "answers", "note", "notes", "tracking_code", "code", "handle",
        "reporter_handle", "signed_url", "url_signature", "prompt", "prompts", "messages",
        "file", "file_bytes", "bytes", "content", "ip", "ip_address", "client_ip", "remote_addr",
        "x_forwarded_for", "client_hmac", "x_shaidago_client_hmac", "pepper", "kek", "dek",
        "private_key", "database_url", "redis_url",
    }
)  # fmt: skip
SENSITIVE_KEY_SUFFIXES: Final = (
    "_password", "_passphrase", "_secret", "_token", "_credential", "_api_key", "_cookie",
    "_pepper", "_hmac",
)  # fmt: skip

_TRACKING_CODE = re.compile(r"\bSG(?:[\s-]?[0-9A-Z]{5}){4}[\s-]?[0-9A-Z]\b", re.IGNORECASE)
_BEARER = re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]+", re.IGNORECASE)
_SESSION_COOKIE = re.compile(r"(?:__Host-)?sg_session=[^;\s]+", re.IGNORECASE)
_SIGNED_URL = re.compile(
    r"https?://[^\s\"']*[?&](?:x-amz-signature|x-amz-credential|signature|sig|token|expires)=[^\s\"']*",
    re.IGNORECASE,
)
# user:password@ inside any URL (database and broker DSNs commonly surface in exception text).
_URL_CREDENTIALS = re.compile(r"(?<=://)[^/\s:@]+:[^@\s/]+@")
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")
# International (+...) or national (leading 0) numbers only, so dates and counters are not caught.
_PHONE = re.compile(r"(?<![\w.])(?:\+\d{1,3}|0)[\d\s()-]{8,}\d(?![\w.])")
_IP_CANDIDATE = re.compile(
    r"(?<![\w:.])(?:[0-9A-Fa-f]{0,4}:){2,7}[0-9A-Fa-f]{0,4}(?![\w:])|\b(?:\d{1,3}\.){3}\d{1,3}\b"
)
# Order matters: URLs and cookies contain fragments the later patterns would otherwise split.
_TEXT_PATTERNS: Final = (
    _SIGNED_URL,
    _URL_CREDENTIALS,
    _BEARER,
    _SESSION_COOKIE,
    _TRACKING_CODE,
    _EMAIL,
    _PHONE,
)


def _is_sensitive_key(key: str) -> bool:
    normalised = key.lower().replace("-", "_")
    return normalised in SENSITIVE_KEYS or normalised.endswith(SENSITIVE_KEY_SUFFIXES)


def _redact_ip(match: re.Match[str]) -> str:
    try:
        ipaddress.ip_address(match.group(0))
    except ValueError:
        return match.group(0)
    return REDACTED


def redact_text(value: str) -> str:
    for pattern in _TEXT_PATTERNS:
        value = pattern.sub(REDACTED, value)
    return _IP_CANDIDATE.sub(_redact_ip, value)


def redact(value: object, *, key: str | None = None) -> Any:
    """Return a copy of ``value`` with sensitive keys and value patterns removed, recursively."""
    if (key is not None and _is_sensitive_key(key)) or isinstance(
        value, (bytes, bytearray, memoryview)
    ):
        return REDACTED
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, Mapping):
        mapping = cast("Mapping[object, object]", value)  # narrowed by isinstance; keys unknown
        return {str(k): redact(v, key=str(k)) for k, v in mapping.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        items = cast("Iterable[object]", value)
        return [redact(item) for item in items]
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return redact_text(str(value))


def _redact_processor(
    _logger: object, _name: str, event_dict: MutableMapping[str, Any]
) -> EventDict:
    return {key: redact(value, key=key) for key, value in event_dict.items()}


def _utc_timestamp(_logger: object, _name: str, event_dict: MutableMapping[str, Any]) -> EventDict:
    event_dict["timestamp"] = datetime.now(UTC).isoformat(timespec="milliseconds")
    return dict(event_dict)


def _service_fields(service: str, environment: str) -> Processor:
    def add(_logger: object, _name: str, event_dict: MutableMapping[str, Any]) -> EventDict:
        event_dict["service"] = service
        event_dict["environment"] = environment
        return dict(event_dict)

    return add


def configure_logging(
    *, service: str, environment: str, level: str, stream: TextIO | None = None
) -> None:
    """Send structlog and stdlib logging (including uvicorn) through the redacting JSON pipeline."""
    shared: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        _utc_timestamp,
        _service_fields(service, environment),
        structlog.processors.format_exc_info,
        _redact_processor,
    ]
    structlog.configure(
        processors=[*shared, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=False,
    )
    handler = logging.StreamHandler(stream or sys.stdout)
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            foreign_pre_chain=[structlog.stdlib.ExtraAdder(), *shared],
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                structlog.processors.JSONRenderer(sort_keys=True),
            ],
        )
    )
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
    # Uvicorn's access log records raw paths and query strings; request logging is ours.
    logging.getLogger("uvicorn.access").disabled = True
