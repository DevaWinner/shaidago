"""Optional anonymous reporter handles (ADR-0005).

A handle is ``SG-H-XXXX-XXXX`` (40 random bits, an identifier and not a secret) and a passphrase of
six words from the EFF long word list (about 77 bits). Both are generated here and shown once;
nothing about a person exists to store, and neither is ever chosen by the user.
"""

import re
import secrets
from collections.abc import Callable
from dataclasses import dataclass
from functools import cache
from importlib.resources import files
from typing import Final

from shaidago.reports.tracking import ALPHABET

HANDLE_SYMBOLS: Final = 8
HANDLE_PREFIX: Final = "SGH"
PASSPHRASE_WORDS: Final = 6
MAX_CREDENTIAL_CHARS: Final = 200
_ALIASES: Final = {"O": "0", "I": "1", "L": "1"}
_SEPARATORS: Final = re.compile(r"[\s\-]+")
_WORDLIST: Final = "wordlists/eff_large_wordlist.txt"


@cache
def wordlist() -> tuple[str, ...]:
    """The 7776 words, in dice order, from the committed and hash-checked EFF list."""
    raw = files("shaidago.reports").joinpath(_WORDLIST).read_text(encoding="utf-8")
    return tuple(line.split("\t", 1)[1] for line in raw.splitlines() if line)


@dataclass(frozen=True)
class NewHandle:
    handle: str
    passphrase: str

    def __repr__(self) -> str:
        return "NewHandle(<redacted>)"


def generate_handle(randbelow: Callable[[int], int] = secrets.randbelow) -> str:
    body = "".join(ALPHABET[randbelow(len(ALPHABET))] for _ in range(HANDLE_SYMBOLS))
    return f"SG-H-{body[:4]}-{body[4:]}"


def generate_passphrase(randbelow: Callable[[int], int] = secrets.randbelow) -> str:
    words = wordlist()
    return " ".join(words[randbelow(len(words))] for _ in range(PASSPHRASE_WORDS))


def generate() -> NewHandle:
    return NewHandle(generate_handle(), generate_passphrase())


def normalise_handle(raw: str) -> str | None:
    """The canonical handle for lenient input, or None. Never raises, never says why."""
    compact = _SEPARATORS.sub("", raw.strip().upper())
    if len(compact) == len(HANDLE_PREFIX) + HANDLE_SYMBOLS:
        compact = compact.removeprefix(HANDLE_PREFIX)  # only when the length says it is a prefix
    canonical = "".join(_ALIASES.get(symbol, symbol) for symbol in compact)
    if len(canonical) != HANDLE_SYMBOLS or any(symbol not in ALPHABET for symbol in canonical):
        return None
    return f"SG-H-{canonical[:4]}-{canonical[4:]}"


def normalise_passphrase(raw: str) -> str:
    """Case and spacing are forgiven; the words themselves are not altered."""
    return " ".join(raw.lower().split())
