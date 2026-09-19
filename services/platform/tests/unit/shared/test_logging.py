import io
import json
import logging
from collections.abc import Iterator
from typing import TYPE_CHECKING

import pytest
import structlog

from shaidago.shared.logging import REDACTED, configure_logging, redact

if TYPE_CHECKING:
    from typing import Any

# Synthetic canaries for every sensitive class the logs must never carry.
TRACKING_CODE = "SG-7GQ2K-9M4XV-C8HTB-3WNZD-R"
SIGNED_URL = "https://files.example.test/o/abc?X-Amz-Signature=deadbeef&X-Amz-Expires=60"
# Values a pattern can recognise wherever they appear.
PATTERN_CANARIES = {
    "cookie": "sg_session=canarysessiontoken123",
    "bearer": "Bearer web.canarybearertoken456",
    "email": "reporter.canary@example.test",
    "phone": "+234 803 555 0142",
    "tracking": TRACKING_CODE,
    "signed_url": SIGNED_URL,
    "ipv4": "203.0.113.77",
    "ipv6": "2001:db8::77:1",
}
# Free text cannot be recognised by pattern; it is protected only by its key.
KEY_CANARIES = {
    "password": "hunter2-canary-password",
    "report": "The contractor canary-report-text abandoned the site",
    "passphrase": "canary-passphrase-six-words-here-now",
}


@pytest.fixture
def stream() -> Iterator[io.StringIO]:
    buffer = io.StringIO()
    configure_logging(service="svc", environment="test", level="DEBUG", stream=buffer)
    yield buffer
    structlog.reset_defaults()
    logging.getLogger().handlers.clear()


def lines(buffer: io.StringIO) -> list[dict[str, Any]]:
    return [json.loads(line) for line in buffer.getvalue().splitlines() if line.strip()]


def test_log_lines_are_json_with_standard_fields(
    stream: io.StringIO,
) -> None:
    structlog.get_logger("t").info("hello", route="/v1/projects", status=200)
    [record] = lines(stream)
    assert record["event"] == "hello"
    assert record["service"] == "svc"
    assert record["environment"] == "test"
    assert record["level"] == "info"
    assert record["route"] == "/v1/projects"
    assert record["timestamp"].endswith("+00:00")


def test_sensitive_keys_are_redacted_regardless_of_value(
    stream: io.StringIO,
) -> None:
    structlog.get_logger("t").info(
        "event",
        password="x",  # noqa: S106 - synthetic value, asserts redaction by key
        Authorization="y",
        tracking_code="z",
        report_text="w",
        client_ip="v",
        reporter_handle="u",
        api_token="t",  # noqa: S106 - synthetic value, asserts redaction by suffix
        nested={"cookie": "s", "safe": "visible"},
    )
    [record] = lines(stream)
    for key in ("password", "Authorization", "tracking_code", "report_text", "client_ip",
                "reporter_handle", "api_token"):  # fmt: skip
        assert record[key] == REDACTED
    assert record["nested"] == {"cookie": REDACTED, "safe": "visible"}


def test_pattern_canaries_never_reach_output_under_innocent_keys_or_messages(
    stream: io.StringIO,
) -> None:
    log = structlog.get_logger("t")
    for canary in PATTERN_CANARIES.values():
        log.info(f"processing {canary}", detail=canary, items=[canary], deep={"x": {"y": canary}})
        logging.getLogger("stdlib").warning("stdlib %s", canary, extra={"detail_value": canary})
    output = stream.getvalue()
    for canary in PATTERN_CANARIES.values():
        assert canary not in output
    assert output.count(REDACTED) >= len(PATTERN_CANARIES)


def test_key_canaries_never_reach_output_under_sensitive_keys(stream: io.StringIO) -> None:
    structlog.get_logger("t").info(
        "submission",
        password=KEY_CANARIES["password"],
        report_text=KEY_CANARIES["report"],
        passphrase=KEY_CANARIES["passphrase"],
    )
    assert not any(canary in stream.getvalue() for canary in KEY_CANARIES.values())


def test_canaries_never_reach_exception_output(stream: io.StringIO) -> None:
    log = structlog.get_logger("t")
    try:
        ipv4, email = PATTERN_CANARIES["ipv4"], PATTERN_CANARIES["email"]
        raise ValueError(f"failed for {TRACKING_CODE} from {ipv4} by {email}")
    except ValueError:
        log.exception("boom")
        logging.getLogger("stdlib").exception("stdlib boom")
    output = stream.getvalue()
    assert "Traceback" in output
    for canary in (TRACKING_CODE, PATTERN_CANARIES["ipv4"], PATTERN_CANARIES["email"]):
        assert canary not in output


def test_bytes_are_never_logged() -> None:
    assert redact({"blob": b"file-bytes", "n": 3, "ok": None}) == {
        "blob": REDACTED,
        "n": 3,
        "ok": None,
    }


def test_non_sensitive_values_and_lookalikes_are_preserved() -> None:
    assert redact("version 1.2.3 built in 42 ms") == "version 1.2.3 built in 42 ms"
    assert redact({"tokens_used": 12, "cache_key": "k"}) == {"tokens_used": 12, "cache_key": "k"}
    assert redact("status 300.400.500.600 unchanged") == "status 300.400.500.600 unchanged"
