"""Fail-closed deterministic validation for provider-authored grounded answers."""

import re
import unicodedata
from dataclasses import dataclass
from typing import Final
from uuid import UUID

from shaidago.projects.models import Locale
from shaidago.retrieval.language import GroundedAnswer

FALLBACK_ANSWER: Final = "The available sources do not confirm this"
MAX_SOURCE_LINKS: Final = 5
MIN_UNION_COVERAGE: Final = 0.6
MIN_CITATION_COVERAGE: Final = 0.4
MIN_SIGNIFICANT_CHARS: Final = 3

_TOKENS: Final = re.compile(r"[^\W_]+", re.UNICODE)
_EMAIL: Final = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE: Final = re.compile(r"(?:\+?\d[\s().-]?){9,}")
_TRACKING: Final = re.compile(
    r"(?<![A-Za-z0-9])S\W{0,2}G\W{0,2}(?:[0-9A-Z]\W{0,2}){21}(?![A-Za-z0-9])", re.I
)
_PERCENT_SCORE: Final = re.compile(r"\b(?:100|[1-9]?\d)\s*%")
_PERSON_TITLE: Final = re.compile(
    r"\b(?:Mr|Mrs|Ms|Miss|Dr|Prof|Chief|Hon|Senator|Malam|Alhaji)\.?\s+[A-Z][^\W\d_]+"
)

_STOPWORDS: Final = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "bụ",
        "da",
        "for",
        "from",
        "fun",
        "in",
        "is",
        "it",
        "ka",
        "ke",
        "na",
        "ne",
        "ni",
        "nke",
        "of",
        "on",
        "ọ",
        "ta",
        "the",
        "ti",
        "to",
        "was",
        "were",
        "ya",
    }
)
_ACCUSATION_TERMS: Final = frozenset(
    {
        "bribe",
        "bribery",
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
        "thief",
    }
)
_EVIDENCE_REQUIRED_TERMS: Final = frozenset({"abandoned", "complete", "completed"})
_FORBIDDEN_PHRASES: Final = (
    "contact details",
    "email address",
    "expose the reporter",
    "ignore previous instructions",
    "identify the reporter",
    "private report",
    "phone number",
    "reporter identity",
    "reveal private",
    "system prompt",
    "tracking code",
    "who reported",
)
_IDENTITY_PHRASES: Final = (
    "identified as",
    "named as the suspect",
    "person responsible is",
    "suspect is",
)


@dataclass(frozen=True)
class CitationEvidence:
    citation_id: str
    project_id: UUID
    passage: str
    source_title: str
    source_url: str
    available: bool


@dataclass(frozen=True)
class SourceLink:
    title: str
    url: str


@dataclass(frozen=True)
class ValidationDecision:
    answer: GroundedAnswer
    source_links: tuple[SourceLink, ...]
    requested_locale: Locale
    served_locale: Locale
    used_provider_answer: bool
    findings: tuple[str, ...]


def _normalised(value: str) -> str:
    return " ".join(_TOKENS.findall(unicodedata.normalize("NFKC", value).casefold()))


def _words(value: str) -> tuple[str, ...]:
    return tuple(_normalised(value).split())


def _significant(value: str) -> set[str]:
    return {
        word
        for word in _words(value)
        if word not in _STOPWORDS
        and (len(word) >= MIN_SIGNIFICANT_CHARS or any(character.isdigit() for character in word))
    }


def _numbers(value: str) -> set[str]:
    return {word for word in _words(value) if any(character.isdigit() for character in word)}


def _coverage(statement: str, passage: str) -> float:
    terms = _significant(statement)
    if not terms:
        return 0.0
    passage_terms = set(_words(passage))
    return len(terms & passage_terms) / len(terms)


def _supports(statement: str, passage: str, *, minimum: float) -> bool:
    normal_statement = _normalised(statement)
    normal_passage = _normalised(passage)
    if normal_statement and normal_statement in normal_passage:
        return True
    numbers = _numbers(statement)
    if not numbers.issubset(set(_words(passage))):
        return False
    return _coverage(statement, passage) >= minimum


def _safety_findings(value: str) -> set[str]:
    normal = _normalised(value)
    words = set(normal.split())
    findings: set[str] = set()
    if words & _ACCUSATION_TERMS:
        findings.add("accusation_or_guilt")
    if _PERSON_TITLE.search(value) or any(phrase in normal for phrase in _IDENTITY_PHRASES):
        findings.add("person_identification")
    if _EMAIL.search(value) or _PHONE.search(value) or _TRACKING.search(value):
        findings.add("private_data")
    if any(phrase in normal for phrase in _FORBIDDEN_PHRASES):
        findings.add("private_data_instruction")
    if _PERCENT_SCORE.search(value) or "truth score" in normal:
        findings.add("truth_score")
    return findings


def statement_supported(statement: str, passage: str) -> bool:
    """Deterministic linkage: the statement is in the passage, or every number in it appears and
    enough of its significant words do."""
    return _supports(statement, passage, minimum=MIN_CITATION_COVERAGE)


def safety_findings(value: str) -> set[str]:
    """Stable finding codes for accusations, identification, private data, and truth scores."""
    return _safety_findings(value)


def _links(evidence: tuple[CitationEvidence, ...], project_id: UUID) -> tuple[SourceLink, ...]:
    values = {
        (item.source_title, item.source_url)
        for item in evidence
        if item.project_id == project_id and item.available
    }
    return tuple(SourceLink(title, url) for title, url in sorted(values))[:MAX_SOURCE_LINKS]


def _fallback(
    answer: GroundedAnswer,
    *,
    locale: Locale,
    project_id: UUID,
    evidence: tuple[CitationEvidence, ...],
    findings: set[str],
) -> ValidationDecision:
    fallback = GroundedAnswer(
        answer=FALLBACK_ANSWER,
        statements=(),
        insufficient_evidence=True,
        confidence_note=FALLBACK_ANSWER,
        generated_at=answer.generated_at,
        locale="en",
    )
    return ValidationDecision(
        answer=fallback,
        source_links=_links(evidence, project_id),
        requested_locale=locale,
        served_locale="en",
        used_provider_answer=False,
        findings=tuple(sorted(findings)),
    )


def _resolve_citations(
    identifiers: tuple[str, ...],
    *,
    indexed: dict[str, list[CitationEvidence]],
    project_id: UUID,
) -> tuple[set[str], list[CitationEvidence]]:
    findings: set[str] = set()
    if not identifiers:
        return {"uncited_statement"}, []
    if len(identifiers) != len(set(identifiers)):
        findings.add("duplicate_citation")
    cited: list[CitationEvidence] = []
    for identifier in dict.fromkeys(identifiers):
        matches = indexed.get(identifier, [])
        if not matches:
            findings.add("unknown_citation")
        elif len(matches) == 1 and matches[0].project_id != project_id:
            findings.add("cross_project_citation")
        elif len(matches) == 1 and not matches[0].available:
            findings.add("unavailable_citation")
        elif len(matches) == 1:
            cited.append(matches[0])
    return findings, cited


def _validate_statement(
    statement_text: str,
    citation_ids: tuple[str, ...],
    *,
    indexed: dict[str, list[CitationEvidence]],
    project_id: UUID,
) -> tuple[set[str], list[CitationEvidence]]:
    findings = _safety_findings(statement_text)
    citation_findings, cited = _resolve_citations(
        citation_ids,
        indexed=indexed,
        project_id=project_id,
    )
    findings.update(citation_findings)
    if not cited:
        return findings, cited
    union = " ".join(item.passage for item in cited)
    if not _supports(statement_text, union, minimum=MIN_UNION_COVERAGE):
        findings.add("unsupported_statement")
    if any(
        not _supports(statement_text, item.passage, minimum=MIN_CITATION_COVERAGE) for item in cited
    ):
        findings.add("unsupported_citation")
    unsupported_guarded = (set(_words(statement_text)) & _EVIDENCE_REQUIRED_TERMS) - set(
        _words(union)
    )
    if unsupported_guarded:
        findings.add("unsupported_guarded_term")
    return findings, cited


def validate_answer(
    answer: GroundedAnswer,
    *,
    expected_locale: Locale,
    project_id: UUID,
    evidence: tuple[CitationEvidence, ...],
) -> ValidationDecision:
    """Return provider prose only when every deterministic trust check passes."""
    findings = _safety_findings(answer.answer) | _safety_findings(answer.confidence_note)
    if answer.locale != expected_locale:
        findings.add("wrong_locale")
    if answer.insufficient_evidence:
        findings.add("insufficient_evidence")
    if not answer.answer.strip() or not answer.statements:
        findings.add("empty_answer")
    joined = " ".join(statement.text.strip() for statement in answer.statements)
    if answer.answer.strip() != joined:
        findings.add("answer_statement_mismatch")

    indexed: dict[str, list[CitationEvidence]] = {}
    for item in evidence:
        indexed.setdefault(item.citation_id, []).append(item)
    if any(len(items) != 1 for items in indexed.values()):
        findings.add("ambiguous_evidence")

    used: list[CitationEvidence] = []
    for statement in answer.statements:
        statement_findings, cited = _validate_statement(
            statement.text,
            statement.citation_ids,
            indexed=indexed,
            project_id=project_id,
        )
        findings.update(statement_findings)
        used.extend(cited)

    if findings:
        return _fallback(
            answer,
            locale=expected_locale,
            project_id=project_id,
            evidence=evidence,
            findings=findings,
        )
    return ValidationDecision(
        answer=answer,
        source_links=_links(tuple(used), project_id),
        requested_locale=expected_locale,
        served_locale=answer.locale,
        used_provider_answer=True,
        findings=(),
    )
