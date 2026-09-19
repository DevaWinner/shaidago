"""Canonical URLs, content hashes, and SimHash near-duplicate detection."""

import hashlib
import re
from typing import Final
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

SIMHASH_BITS: Final = 64
NEAR_DUPLICATE_DISTANCE: Final = 3
_SHINGLE_WORDS: Final = 3
_TRACKING_PARAMS: Final = re.compile(r"^(utm_.*|fbclid|gclid|mc_cid|mc_eid|ref|source)$", re.I)
_WORD: Final = re.compile(r"\w+", re.UNICODE)
_MASK: Final = (1 << SIMHASH_BITS) - 1


def canonical_url(url: str) -> str:
    """A stable form: lower-case scheme and host, no fragment, default port, tracking parameters,
    or trailing slash on a non-root path, and query parameters in sorted order."""
    parts = urlsplit(url.strip())
    host = (parts.hostname or "").lower().rstrip(".")
    default = 443 if parts.scheme == "https" else 80
    netloc = host if parts.port in (None, default) else f"{host}:{parts.port}"
    path = parts.path or "/"
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")
    query = urlencode(
        sorted((k, v) for k, v in parse_qsl(parts.query) if not _TRACKING_PARAMS.match(k))
    )
    return urlunsplit((parts.scheme.lower(), netloc, path, query, ""))


def normalise_text(text: str) -> str:
    return " ".join(_WORD.findall(text.casefold()))


def content_sha256(text: str) -> str:
    return hashlib.sha256(normalise_text(text).encode()).hexdigest()


def simhash64(text: str) -> int:
    """A 64-bit SimHash of word shingles, as a signed integer (PostgreSQL ``bigint``)."""
    words = _WORD.findall(text.casefold())
    if not words:
        return 0
    shingles = (
        [" ".join(words[i : i + _SHINGLE_WORDS]) for i in range(len(words) - _SHINGLE_WORDS + 1)]
        if len(words) >= _SHINGLE_WORDS
        else [" ".join(words)]
    )
    weights = [0] * SIMHASH_BITS
    for shingle in shingles:
        digest = int.from_bytes(hashlib.sha256(shingle.encode()).digest()[:8], "big")
        for bit in range(SIMHASH_BITS):
            weights[bit] += 1 if digest >> bit & 1 else -1
    value = sum(1 << bit for bit, weight in enumerate(weights) if weight > 0)
    return value - (1 << SIMHASH_BITS) if value >> (SIMHASH_BITS - 1) else value


def hamming(a: int, b: int) -> int:
    return ((a ^ b) & _MASK).bit_count()
