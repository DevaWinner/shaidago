"""Typed grounded-answer provider boundary and deterministic replay fixtures."""

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from shaidago.projects.models import Locale

PROMPT_VERSION = "grounded-qa-v1"
SCHEMA_VERSION = "grounded-answer-v1"
MAX_PASSAGES = 5
MAX_FIXTURE_BYTES = 256 * 1024
QA_FIXTURES_ROOT = Path(__file__).parents[5] / "data" / "qa-fixtures"
CitationId = Annotated[str, Field(pattern=r"^c_[a-z0-9]{8,40}$", max_length=42)]


class RetryClass(StrEnum):
    RETRYABLE = "retryable"
    NON_RETRYABLE = "non_retryable"
    POLICY_FAILURE = "policy_failure"


class LanguageModelError(Exception):
    """A provider-safe failure that never includes upstream content or request text."""

    def __init__(self, code: str, retry_class: RetryClass) -> None:
        self.code = code
        self.retry_class = retry_class
        super().__init__(code)


class EvidencePassage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    citation_id: CitationId
    text: str = Field(min_length=1, max_length=900)


class GroundedAnswerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    locale: Locale
    question: str = Field(min_length=1, max_length=300)
    passages: tuple[EvidencePassage, ...] = Field(min_length=1, max_length=MAX_PASSAGES)
    generated_at: datetime

    @field_validator("passages")
    @classmethod
    def _unique_citation_ids(
        cls, value: tuple[EvidencePassage, ...]
    ) -> tuple[EvidencePassage, ...]:
        identifiers = [passage.citation_id for passage in value]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("citation IDs must be unique")
        return value

    @field_validator("generated_at")
    @classmethod
    def _utc_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("generated_at must be UTC-aware")
        return value.astimezone(UTC)


class AnswerStatement(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    text: str = Field(min_length=1, max_length=1200)
    citation_ids: tuple[CitationId, ...] = Field(min_length=1, max_length=MAX_PASSAGES)


class _StructuredAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    answer: str = Field(max_length=4000)
    statements: tuple[AnswerStatement, ...] = Field(max_length=8)
    insufficient_evidence: bool
    confidence_note: str = Field(min_length=1, max_length=500)
    generated_at: str = Field(min_length=20, max_length=40)


class _FixtureAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    answer: str = Field(max_length=4000)
    statements: tuple[AnswerStatement, ...] = Field(max_length=8)
    insufficient_evidence: bool
    confidence_note: str = Field(min_length=1, max_length=500)


class _FixtureRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    output: _FixtureAnswer


class _FixtureFile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    fixture_version: Literal[1]
    records: tuple[_FixtureRecord, ...] = Field(min_length=1, max_length=100)


@dataclass(frozen=True)
class GroundedAnswer:
    answer: str
    statements: tuple[AnswerStatement, ...]
    insufficient_evidence: bool
    confidence_note: str
    generated_at: datetime


@dataclass(frozen=True)
class LanguageModelResult:
    answer: GroundedAnswer
    model_id: str
    prompt_version: str
    schema_version: str
    demo_replay: bool


class LanguageModel(Protocol):
    model_id: str

    async def answer(self, request: GroundedAnswerRequest) -> LanguageModelResult: ...


def generated_at_text(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def structured_answer_schema() -> dict[str, object]:
    """Return the strict JSON Schema sent to the provider."""
    return _StructuredAnswer.model_json_schema()


def parse_structured_answer(raw: str, *, expected_generated_at: datetime) -> GroundedAnswer:
    try:
        parsed = _StructuredAnswer.model_validate_json(raw)
    except ValidationError as error:
        raise LanguageModelError("provider_invalid_schema", RetryClass.NON_RETRYABLE) from error
    expected = generated_at_text(expected_generated_at)
    if parsed.generated_at != expected:
        raise LanguageModelError("provider_invalid_timestamp", RetryClass.NON_RETRYABLE)
    return GroundedAnswer(
        answer=parsed.answer,
        statements=parsed.statements,
        insufficient_evidence=parsed.insufficient_evidence,
        confidence_note=parsed.confidence_note,
        generated_at=expected_generated_at,
    )


def request_fingerprint(request: GroundedAnswerRequest) -> str:
    """Fingerprint semantic input; application time is injected into replay output separately."""
    payload = {
        "locale": request.locale,
        "passages": [passage.model_dump(mode="json") for passage in request.passages],
        "prompt_version": PROMPT_VERSION,
        "question": request.question,
        "schema_version": SCHEMA_VERSION,
    }
    encoded = json.dumps(
        payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def provider_input(request: GroundedAnswerRequest) -> str:
    """Serialise only the destination allowlist: question, locale, public passages and IDs."""
    payload = {
        "generated_at": generated_at_text(request.generated_at),
        "locale": request.locale,
        "passages": [passage.model_dump(mode="json") for passage in request.passages],
        "question": request.question,
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


class FixtureLanguageModel:
    """Checked-in structured answers keyed by a stable request fingerprint."""

    def __init__(
        self,
        records: Mapping[str, _FixtureAnswer],
        *,
        model_id: str = "fixture-grounded-qa-v1",
    ) -> None:
        self.model_id = model_id
        self._records = dict(records)

    @classmethod
    def from_path(cls, path: Path) -> FixtureLanguageModel:
        if path.stat().st_size > MAX_FIXTURE_BYTES:
            raise ValueError("Q&A fixture is too large")
        try:
            fixture = _FixtureFile.model_validate_json(path.read_text(encoding="utf-8"))
        except ValidationError as error:
            raise ValueError("Q&A fixture has an invalid shape") from error
        records: dict[str, _FixtureAnswer] = {}
        for record in fixture.records:
            if record.fingerprint in records:
                raise ValueError("Q&A fixture duplicates a request fingerprint")
            records[record.fingerprint] = record.output
        return cls(records)

    async def answer(self, request: GroundedAnswerRequest) -> LanguageModelResult:
        fixture = self._records.get(request_fingerprint(request))
        if fixture is None:
            raise LanguageModelError("provider_fixture_missing", RetryClass.NON_RETRYABLE)
        raw = json.dumps(
            fixture.model_dump(mode="json")
            | {"generated_at": generated_at_text(request.generated_at)},
            ensure_ascii=False,
            separators=(",", ":"),
        )
        return LanguageModelResult(
            answer=parse_structured_answer(raw, expected_generated_at=request.generated_at),
            model_id=self.model_id,
            prompt_version=PROMPT_VERSION,
            schema_version=SCHEMA_VERSION,
            demo_replay=True,
        )
