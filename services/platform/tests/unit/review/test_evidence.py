"""The download broker's pure rules: what may be served and how it is presented."""

from uuid import uuid4

import pytest

from shaidago.review.evidence import (
    EvidenceRecord,
    content_headers,
    download_filename,
    is_servable,
)


def record(**overrides: object) -> EvidenceRecord:
    base: dict[str, object] = {
        "id": uuid4(),
        "object_key": "a" * 32,
        "display_name": "site photo.png",
        "mime_type": "image/png",
        "size_bytes": 10,
        "sha256": "b" * 64,
        "sanitation_state": "sanitised",
        "scan_state": "clean",
    }
    return EvidenceRecord(**(base | overrides))  # type: ignore[arg-type]


@pytest.mark.parametrize("scan_state", ["clean", "not_scanned_demo"])
def test_sanitised_evidence_with_a_known_scan_state_is_servable(scan_state: str) -> None:
    assert is_servable(record(scan_state=scan_state))


@pytest.mark.parametrize(
    "overrides",
    [
        {"sanitation_state": "pending"},
        {"sanitation_state": ""},
        {"sanitation_state": "rejected"},
        {"scan_state": "infected"},
        {"scan_state": "scan_failed"},
        {"scan_state": ""},
        {"mime_type": "text/html"},
        {"mime_type": "image/svg+xml"},
        {"mime_type": "application/octet-stream"},
    ],
)
def test_anything_else_is_refused(overrides: dict[str, object]) -> None:
    assert not is_servable(record(**overrides))


@pytest.mark.parametrize(
    ("display_name", "expected"),
    [
        ("site photo.png", "site photo.png"),
        ('a"b\r\nX-Injected: 1.png', "abX-Injected 1.png"),
        ("../../etc/passwd.png", "etcpasswd.png"),
        ("....png", "evidence.png"),
        ("", "evidence.png"),
        ("naïve.png", "nave.png"),
        ("x" * 200 + ".png", "x" * 60 + ".png"),
    ],
)
def test_the_download_name_is_plain_ascii_with_the_type_extension(
    display_name: str, expected: str
) -> None:
    assert download_filename(record(display_name=display_name)) == expected


def test_the_extension_follows_the_stored_type_not_the_name() -> None:
    assert download_filename(record(display_name="report.exe", mime_type="application/pdf")) == (
        "report.pdf"
    )


def test_headers_force_a_download_and_forbid_caching_and_sniffing() -> None:
    headers = content_headers(record(scan_state="not_scanned_demo"))
    assert headers["Content-Disposition"] == 'attachment; filename="site photo.png"'
    assert headers["Content-Type"] == "image/png"
    assert headers["Cache-Control"] == "no-store"
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert "sandbox" in headers["Content-Security-Policy"]
    assert headers["X-Evidence-Scan-State"] == "not_scanned_demo"
    assert not any("a" * 32 in value for value in headers.values())
