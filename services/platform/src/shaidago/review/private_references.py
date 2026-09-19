"""Deterministic checks that a public update repeats nothing private and claims nothing unsupported.

Pure functions with no I/O, so every branch is testable. The checks are a floor, not a
substitute for the reviewer's judgement or the preview step: they refuse a public statement that
contains a tracking code, a reporter handle, a contact value (or any email or phone-like text),
a reviewer's name, a run of words copied from the private report, answers, or notes, or a strong
accusatory or completion word that no cited passage itself contains.
"""

import re
from dataclasses import dataclass
from typing import Final

SHINGLE_WORDS: Final = 6
_MIN_CONTACT_CHARS: Final = 3
_MIN_PHONE_DIGITS: Final = 7
# A code starts at a token boundary (so "pages give ..." is not "SG" plus 21 letters) and may be
# spaced, dashed, or punctuated between characters.
_TRACKING_BODY: Final = re.compile(
    r"(?<![A-Za-z0-9])S\W{0,2}G\W{0,2}(?:[0-9A-Z]\W{0,2}){21}(?![A-Za-z0-9])", re.I
)
_HANDLE_BODY: Final = re.compile(
    r"(?<![A-Za-z0-9])S\W{0,2}G\W{0,2}H\W{0,2}(?:[0-9A-Z]\W{0,2}){8}(?![A-Za-z0-9])", re.I
)
_EMAIL: Final = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE: Final = re.compile(r"(?:\+?\d[\s().-]?){9,}")
_WORDS: Final = re.compile(r"[a-z0-9]+")
# Wording that must be backed by an exact passage (AGENTS.md: never call a project corrupt,
# fraudulent, abandoned, or complete without exact reliable evidence).
GUARDED_TERMS: Final = (
    "abandoned",
    "bribe",
    "bribery",
    "complete",
    "completed",
    "corrupt",
    "corruption",
    "criminal",
    "embezzled",
    "embezzlement",
    "fraud",
    "fraudulent",
    "guilty",
    "scam",
    "stolen",
)


@dataclass(frozen=True)
class PrivateContext:
    """Everything private about one report that a public statement must not repeat."""

    texts: tuple[str, ...] = ()
    contact_values: tuple[str, ...] = ()
    handles: tuple[str, ...] = ()
    reviewer_names: tuple[str, ...] = ()

    def __repr__(self) -> str:
        return "PrivateContext(<redacted>)"


def _words(value: str) -> list[str]:
    return _WORDS.findall(value.lower())


def _has_shingle(statement_words: list[str], private_words: list[str]) -> bool:
    if not private_words or not statement_words:
        return False
    size = min(SHINGLE_WORDS, len(private_words))
    statement_grams = {
        tuple(statement_words[i : i + size]) for i in range(len(statement_words) - size + 1)
    }
    return any(
        tuple(private_words[i : i + size]) in statement_grams
        for i in range(len(private_words) - size + 1)
    )


def _mentions_name(statement: str, name: str) -> bool:
    cleaned = name.strip().lower()
    if len(cleaned) < _MIN_CONTACT_CHARS:
        return False
    pattern = r"(?<![a-z0-9])" + re.escape(cleaned) + r"(?![a-z0-9])"
    return re.search(pattern, statement.lower()) is not None


def _mentions_contact(statement: str, value: str) -> bool:
    cleaned = value.strip().lower()
    if len(cleaned) < _MIN_CONTACT_CHARS:
        return False
    if cleaned in statement.lower():
        return True
    digits = re.sub(r"\D", "", cleaned)
    return len(digits) >= _MIN_PHONE_DIGITS and digits in re.sub(r"\D", "", statement)


def find_private_references(statement: str, private: PrivateContext) -> tuple[str, ...]:
    """Stable finding codes for anything private in ``statement``; empty means none found."""
    found: set[str] = set()
    squeezed = re.sub(r"[^0-9A-Za-z]", "", statement).upper()
    if _TRACKING_BODY.search(statement):
        found.add("tracking_code")
    if _HANDLE_BODY.search(statement) or any(
        re.sub(r"[^0-9A-Za-z]", "", h).upper() in squeezed for h in private.handles if h
    ):
        found.add("reporter_handle")
    if (
        _EMAIL.search(statement)
        or _PHONE.search(statement)
        or any(_mentions_contact(statement, value) for value in private.contact_values)
    ):
        found.add("contact")
    if any(_mentions_name(statement, name) for name in private.reviewer_names):
        found.add("reviewer_name")
    statement_words = _words(statement)
    if any(_has_shingle(statement_words, _words(text)) for text in private.texts):
        found.add("report_text")
    return tuple(sorted(found))


def unsupported_terms(statement: str, passages: list[str]) -> tuple[str, ...]:
    """Guarded words in the statement that no cited passage contains, sorted and unique."""
    cited = {word for passage in passages for word in _words(passage)}
    return tuple(sorted({w for w in _words(statement) if w in GUARDED_TERMS and w not in cited}))
