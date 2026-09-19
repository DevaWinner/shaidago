"""Limits, rejection reasons, type sniffing, and file-name sanitising for evidence uploads."""

import re
import unicodedata
from dataclasses import dataclass
from typing import Final, Literal

MIME_EXTENSIONS: Final = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "application/pdf": "pdf",
}
Reason = Literal[
    "unsupported_type",
    "spoofed_type",
    "active_content",
    "encrypted_pdf",
    "too_large",
    "too_many_pixels",
    "too_many_pages",
    "malformed",
    "malware_detected",
    "scan_failed",
    "storage_failed",
    "timeout",
]
_ACTIVE_MARKERS: Final = (b"<script", b"<svg", b"<html", b"javascript:", b"<?php", b"<iframe")
_SCAN_WINDOW: Final = 65536


@dataclass(frozen=True)
class FileLimits:
    max_file_bytes: int = 10 * 1024 * 1024
    max_pixels: int = 25_000_000
    max_dimension: int = 4096  # longer sides are scaled down to this, keeping the aspect ratio
    max_pdf_pages: int = 20
    chunk_bytes: int = 64 * 1024
    sanitise_timeout_seconds: float = 20.0
    scan_timeout_seconds: float = 15.0
    store_timeout_seconds: float = 15.0


class UploadRejectedError(Exception):
    """An upload was refused. ``reason`` is a stable code; nothing about the content is kept."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def sniff(head: bytes) -> str | None:
    """The real type from magic bytes, or None if it is not an allowed evidence type."""
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    if head.startswith(b"%PDF-"):
        return "application/pdf"
    return None


def has_active_content(data: bytes) -> bool:
    """Script, markup, or a second document hiding at either end of an image (a polyglot)."""
    windows = (data[:_SCAN_WINDOW].lower(), data[-_SCAN_WINDOW:].lower())
    if any(marker in window for window in windows for marker in _ACTIVE_MARKERS):
        return True
    return b"%pdf-" in data[8:].lower()[:_SCAN_WINDOW] or b"%pdf-" in windows[1]


def safe_display_name(raw: str, mime: str) -> str:
    """A short plain name with the sniffed type's extension; no path or control characters."""
    base = raw.replace("\\", "/").rsplit("/", 1)[-1]
    base = unicodedata.normalize("NFKD", base).encode("ascii", "ignore").decode("ascii")
    stem = re.sub(r"[^A-Za-z0-9 _-]", "", base.rsplit(".", 1)[0]).strip(" .-_")[:60]
    return f"{stem or 'evidence'}.{MIME_EXTENSIONS[mime]}"
