"""The privacy-safe query planner: what may leave the system in a web search, and nothing else.

A query is built only from an allowlist: the public project's own title, locality, authority and
category, public years, and (for a report-scoped run) neutral incident concepts drawn from a
fixed vocabulary. Anything else is excluded, never sent. Each candidate term is also screened by
deterministic detectors (email, phone, URL, credentials, coordinates, tracking-code and handle
patterns, and obfuscated variants of each), so an uncertain term is dropped rather than risked.
AI may *suggest* concepts, but a suggestion is used only if it is in the vocabulary and passes
the detectors; the model never bypasses the rules.
"""

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from typing import Final, Literal

POLICY_VERSION: Final = "query-policy-2026-09-v1"
MAX_QUERY_CHARS: Final = 300
MAX_TERM_CHARS: Final = 80
MAX_TERMS: Final = 12
_MAX_PLAIN_DIGITS: Final = 4  # a year fits; a phone number or identifier does not

TermSource = Literal[
    "project_title", "locality", "authority", "category", "public_year", "incident_concept"
]

# Neutral words that describe public works, never a person, place, or allegation.
CONCEPT_VOCABULARY: Final = frozenset(
    {
        "construction", "building", "road", "bridge", "drainage", "borehole", "water", "clinic",
        "health", "hospital", "school", "classroom", "market", "electricity", "streetlight",
        "unfinished", "delayed", "delay", "incomplete", "stalled", "contract", "procurement",
        "budget", "funding", "completion", "inspection", "safety", "quality", "materials",
        "site", "works", "project", "status", "update", "renovation", "rehabilitation",
    }
)  # fmt: skip

_ZERO_WIDTH: Final = dict.fromkeys(
    [0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF, 0x00AD, 0x180E, 0x200E, 0x200F], None
)
_EMAIL: Final = re.compile(
    r"[\w.+-]+\s*(?:@|\bat\b|\[at\]|\(at\))\s*[\w-]+\s*(?:\.|\bdot\b|\[dot\]|\(dot\))\s*\w+"
)
_URL: Final = re.compile(r"(?:https?://|www\.|\b\w+\.(?:com|org|net|ng|gov|edu|io|co)\b)", re.I)
_CREDENTIAL: Final = re.compile(
    r"(?:password|passwd|passphrase|secret|token|apikey|api[-_ ]key|bearer|authorization)", re.I
)
_LONG_TOKEN: Final = re.compile(r"\b[A-Za-z0-9+/_=-]{20,}\b")
_TRACKING: Final = re.compile(r"\bs\W*g\W*(?:h\W*)?(?:[0-9a-z]\W*){5,}", re.I)
_COORDINATE: Final = re.compile(r"[-+]?\d{1,3}[.,]\d{3,}\s*[,;/ ]\s*[-+]?\d{1,3}[.,]\d{3,}")
_DIGITISH: Final = re.compile(r"[0-9oOlI][0-9oOlI\s().+-]{5,}[0-9oOlI]")
_YEAR: Final = re.compile(r"(?<!\d)(?:19|20)\d{2}(?!\d)")
_WORD: Final = re.compile(r"[^\W\d_]+", re.UNICODE)


class UnsafeQueryError(ValueError):
    """A query failed the outbound check. The message never repeats it."""


@dataclass(frozen=True)
class Term:
    text: str
    source: TermSource
    suggested_by: Literal["allowlist", "ai_suggestion"] = "allowlist"


@dataclass(frozen=True)
class Rejection:
    """A candidate that was not used, with a stable reason but never the text itself."""

    source: str
    reason: str


@dataclass(frozen=True)
class PublicProjectTerms:
    title: str
    locality: str | None = None
    authority: str | None = None
    category: str | None = None
    years: tuple[int, ...] = ()


@dataclass(frozen=True)
class QueryPlan:
    terms: tuple[Term, ...]
    query: str
    policy_version: str
    rejected: tuple[Rejection, ...]

    @property
    def digest(self) -> str:
        """Identifies exactly what would be sent; any change to it needs a new approval."""
        return hashlib.sha256(f"{self.policy_version}\n{self.query}".encode()).hexdigest()


def _normalise(value: str) -> str:
    folded = unicodedata.normalize("NFKC", value).translate(_ZERO_WIDTH)
    return re.sub(r"\s+", " ", folded).strip()


def sensitive_reason(value: str) -> str | None:
    """Why ``value`` looks sensitive, or None. Errs toward flagging."""
    text = _normalise(value)
    squeezed = re.sub(r"[\s._\-]+", "", text.casefold())
    checks = (
        ("email", bool(_EMAIL.search(text.casefold())) or "@" in text),
        ("url", bool(_URL.search(text))),
        ("credential", bool(_CREDENTIAL.search(text)) or bool(_LONG_TOKEN.search(text))),
        ("tracking_code", bool(_TRACKING.search(text)) or squeezed.startswith("sgh")),
        ("coordinates", bool(_COORDINATE.search(text))),
        ("phone_or_identifier", _too_many_digits(text)),
    )
    return next((name for name, hit in checks if hit), None)


def _too_many_digits(text: str) -> bool:
    # Standalone plausible years are public and allowed; every other digit counts.
    remainder = _YEAR.sub(" ", text)
    if sum(ch.isdigit() for ch in remainder) > _MAX_PLAIN_DIGITS:
        return True
    return any(
        sum(ch in "0123456789oOlI" for ch in match.group()) >= 7  # noqa: PLR2004 - phone-length run
        for match in _DIGITISH.finditer(remainder)
    )


def screen_term(text: str, *, source: str) -> tuple[str | None, Rejection | None]:
    """The cleaned term, or a rejection. Text longer than a short phrase is never used."""
    cleaned = _normalise(text)
    if not cleaned:
        return None, Rejection(source, "empty")
    if len(cleaned) > MAX_TERM_CHARS:
        return None, Rejection(source, "too_long")
    reason = sensitive_reason(cleaned)
    if reason is not None:
        return None, Rejection(source, reason)
    return cleaned, None


def _assemble(terms: list[Term], rejected: list[Rejection]) -> QueryPlan:
    seen: set[str] = set()
    kept: list[Term] = []
    length = 0
    for term in terms:
        key = term.text.casefold()
        if key in seen:
            continue
        added = len(term.text) + (1 if kept else 0)
        if len(kept) >= MAX_TERMS or length + added > MAX_QUERY_CHARS:
            rejected.append(Rejection(term.source, "over_budget"))
            continue
        seen.add(key)
        kept.append(term)
        length += added
    query = " ".join(t.text for t in kept)
    plan = QueryPlan(tuple(kept), query, POLICY_VERSION, tuple(rejected))
    if kept:  # an empty plan is legal; the caller must not search with it
        assert_query_safe(plan.query)
    return plan


def _public_terms(project: PublicProjectTerms, rejected: list[Rejection]) -> list[Term]:
    candidates: list[tuple[str, TermSource]] = [(project.title, "project_title")]
    if project.locality:
        candidates.append((project.locality, "locality"))
    if project.authority:
        candidates.append((project.authority, "authority"))
    if project.category:
        candidates.append((project.category, "category"))
    years: list[tuple[str, TermSource]] = [
        (str(y), "public_year")
        for y in project.years
        if 1900 <= y <= 2100  # noqa: PLR2004
    ]
    candidates += years
    terms: list[Term] = []
    for value, source in candidates:
        cleaned, rejection = screen_term(value, source=source)
        if cleaned is not None:
            terms.append(Term(cleaned, source))
        elif rejection is not None:
            rejected.append(rejection)
    return terms


def plan_public_query(project: PublicProjectTerms) -> QueryPlan:
    """A query from public project fields only."""
    rejected: list[Rejection] = []
    return _assemble(_public_terms(project, rejected), rejected)


def plan_report_query(
    project: PublicProjectTerms, suggested_concepts: list[str], *, ai_suggested: bool = True
) -> QueryPlan:
    """Public terms plus only those suggested concepts that are wholly neutral vocabulary."""
    rejected: list[Rejection] = []
    terms = _public_terms(project, rejected)
    origin: Literal["allowlist", "ai_suggestion"] = "ai_suggestion" if ai_suggested else "allowlist"
    for suggestion in suggested_concepts[:20]:
        cleaned, rejection = screen_term(suggestion, source="incident_concept")
        if cleaned is None:
            if rejection is not None:
                rejected.append(rejection)
            continue
        words = [w.casefold() for w in _WORD.findall(cleaned)]
        if not words or len(words) > 3 or any(w not in CONCEPT_VOCABULARY for w in words):  # noqa: PLR2004
            rejected.append(Rejection("incident_concept", "not_in_vocabulary"))
            continue
        terms.append(Term(" ".join(words), "incident_concept", origin))
    return _assemble(terms, rejected)


def assert_query_safe(query: str) -> None:
    """The last check before anything is sent: no term may look sensitive. Raises, never sends."""
    if not query.strip() or len(query) > MAX_QUERY_CHARS:
        raise UnsafeQueryError("query length")
    if sensitive_reason(query) is not None:
        raise UnsafeQueryError("query content")


def approval_matches(
    plan: QueryPlan, approved_query: str | None, approved_policy: str | None
) -> bool:
    """An approval covers exactly one query under one policy version; any change needs a new one."""
    return approved_query == plan.query and approved_policy == plan.policy_version
