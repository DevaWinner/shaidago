"""Tracking codes: ``SG-XXXXX-XXXXX-XXXXX-XXXXX-C`` (ADR-0005).

Twenty Crockford Base32 symbols carry 100 random bits; one Luhn mod 32 check symbol catches typos.
The raw code is shown once, in the create response, and is never stored, logged, or put in a URL:
the database keeps only ``HMAC-SHA-256(pepper, normalised code)``. Normalisation is deliberately
strict: it maps only the Crockford look-alikes (O to 0, I and L to 1) and rejects everything else,
so a typo can never silently match a different code.
"""

import hashlib
import hmac
import secrets
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Final

ALPHABET: Final = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"  # Crockford: no I, L, O, or U
_VALUE = {symbol: index for index, symbol in enumerate(ALPHABET)}
_ALIASES: Final = {"O": "0", "I": "1", "L": "1"}
BODY_SYMBOLS: Final = 20
CODE_SYMBOLS: Final = BODY_SYMBOLS + 1
PREFIX: Final = "SG"
CHECKSUM_VERSION: Final = 1
ENTROPY_BYTES: Final = 13  # 104 bits drawn; the top 100 are used
_SEPARATORS: Final = str.maketrans("", "", " -")
MAX_GENERATION_ATTEMPTS: Final = 5
_LOOKUP_DOMAIN: Final = b"sg-track-v1:"


class InvalidTrackingCodeError(ValueError):
    """The text is not a valid tracking code. The message never repeats the input."""

    def __init__(self) -> None:
        super().__init__("not a valid tracking code")


class CodeGenerationError(RuntimeError):
    """Could not find an unused code within the bounded number of attempts."""


def _luhn_mod32(body: str) -> str:
    """Check symbol over the 20 body symbols (Luhn's algorithm generalised to base 32)."""
    total = 0
    factor = 2
    for symbol in reversed(body):
        addend = _VALUE[symbol] * factor
        factor = 1 if factor == 2 else 2  # noqa: PLR2004 - Luhn alternates 2 and 1
        total += addend // 32 + addend % 32
    return ALPHABET[(32 - total % 32) % 32]


@dataclass(frozen=True)
class TrackingCode:
    """A validated code in canonical form: 20 body symbols then the check symbol."""

    canonical: str

    def __repr__(self) -> str:
        return "TrackingCode(<redacted>)"

    __str__ = __repr__

    @property
    def formatted(self) -> str:
        """``SG-XXXXX-XXXXX-XXXXX-XXXXX-C``. Use only to build the one-time create response."""
        body = self.canonical[:BODY_SYMBOLS]
        groups = "-".join(body[i : i + 5] for i in range(0, BODY_SYMBOLS, 5))
        return f"{PREFIX}-{groups}-{self.canonical[BODY_SYMBOLS]}"


def generate(random_bytes: Callable[[int], bytes] = secrets.token_bytes) -> TrackingCode:
    """A fresh code from a secure, injectable byte source (called exactly once)."""
    drawn = int.from_bytes(random_bytes(ENTROPY_BYTES), "big") >> (ENTROPY_BYTES * 8 - 100)
    body = "".join(ALPHABET[(drawn >> shift) & 31] for shift in range(95, -1, -5))
    return TrackingCode(body + _luhn_mod32(body))


def generate_unique(
    is_taken: Callable[[TrackingCode], bool],
    random_bytes: Callable[[int], bytes] = secrets.token_bytes,
) -> TrackingCode:
    """Retry on the (astronomically unlikely) collision, then fail rather than loop forever."""
    for _ in range(MAX_GENERATION_ATTEMPTS):
        candidate = generate(random_bytes)
        if not is_taken(candidate):
            return candidate
    raise CodeGenerationError


def normalise(raw: str) -> TrackingCode:
    """Validate typed input. Raises ``InvalidTrackingCodeError`` before any database work."""
    compact = raw.upper().translate(_SEPARATORS)
    if len(compact) == CODE_SYMBOLS + len(PREFIX):
        # "S" and "G" are valid symbols, so the prefix is recognised by length, never by content.
        if not compact.startswith(PREFIX):
            raise InvalidTrackingCodeError
        compact = compact[len(PREFIX) :]
    if len(compact) != CODE_SYMBOLS:
        raise InvalidTrackingCodeError
    canonical = "".join(_ALIASES.get(symbol, symbol) for symbol in compact)
    if any(symbol not in _VALUE for symbol in canonical):
        raise InvalidTrackingCodeError
    if _luhn_mod32(canonical[:BODY_SYMBOLS]) != canonical[BODY_SYMBOLS]:
        raise InvalidTrackingCodeError
    return TrackingCode(canonical)


def lookup_key(pepper: bytes, code: TrackingCode) -> bytes:
    """The only value stored or indexed for a code."""
    return hmac.new(pepper, _LOOKUP_DOMAIN + code.canonical.encode(), hashlib.sha256).digest()


def lookup_candidates(
    peppers: Mapping[str, bytes], active_version: str, code: TrackingCode
) -> list[tuple[str, bytes]]:
    """Keys to try: the active pepper first, then retired ones (a retired hit is rehashed)."""
    ordered = [active_version, *sorted(v for v in peppers if v != active_version)]
    return [(version, lookup_key(peppers[version], code)) for version in ordered]
