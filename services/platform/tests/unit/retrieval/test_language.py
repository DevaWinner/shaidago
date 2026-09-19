import json
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import pytest
from pydantic import ValidationError

from shaidago.retrieval.language import (
    QA_FIXTURES_ROOT,
    EvidencePassage,
    FixtureLanguageModel,
    GroundedAnswerRequest,
    LanguageModelError,
    RetryClass,
    generated_at_text,
    provider_input,
    request_fingerprint,
    structured_answer_schema,
)

NOW = datetime(2026, 9, 19, 17, 0, tzinfo=UTC)
DOCUMENT = "Synthetic document. The synthetic clinic opened on 1 March. Section two follows."


def request(*, now: datetime = NOW) -> GroundedAnswerRequest:
    return GroundedAnswerRequest(
        locale="en",
        question="What opened?",
        passages=(EvidencePassage(citation_id="c_synthetic01", text=DOCUMENT),),
        generated_at=now,
    )


def test_request_is_strict_bounded_and_requires_unique_opaque_citations() -> None:
    with pytest.raises(ValidationError, match="citation IDs must be unique"):
        GroundedAnswerRequest(
            locale="en",
            question="What opened?",
            passages=(
                EvidencePassage(citation_id="c_duplicate1", text="first"),
                EvidencePassage(citation_id="c_duplicate1", text="second"),
            ),
            generated_at=NOW,
        )
    with pytest.raises(ValidationError, match="UTC-aware"):
        GroundedAnswerRequest(
            locale="en",
            question="What opened?",
            passages=(EvidencePassage(citation_id="c_synthetic01", text=DOCUMENT),),
            generated_at=NOW.replace(tzinfo=None),
        )
    with pytest.raises(ValidationError):
        EvidencePassage(citation_id="database-uuid-is-not-opaque", text=DOCUMENT)


def test_fingerprint_is_stable_and_application_timestamp_is_not_fixture_identity() -> None:
    later = NOW.replace(hour=18)
    assert request_fingerprint(request()) == request_fingerprint(request(now=later))
    assert request_fingerprint(request()) == (
        "09febe0a1ebb180864ff1d3d8b7869897a66382473761a0bb1ecf8c348e372d0"
    )


def test_provider_input_contains_only_the_destination_allowlist() -> None:
    body = json.loads(provider_input(request()))
    assert set(body) == {"generated_at", "locale", "passages", "question"}
    assert set(body["passages"][0]) == {"citation_id", "text"}
    assert body["generated_at"] == generated_at_text(NOW)


async def test_checked_fixture_replays_structured_output_and_injects_application_time() -> None:
    path = QA_FIXTURES_ROOT / "grounded-qa-v1.json"
    fixture = FixtureLanguageModel.from_path(path)
    result = await fixture.answer(request())

    assert result.demo_replay is True
    assert result.answer.generated_at == NOW
    assert result.answer.statements[0].citation_ids == ("c_synthetic01",)
    raw = path.read_text(encoding="utf-8")
    assert "What opened?" not in raw
    assert DOCUMENT not in raw


async def test_fixture_miss_is_explicit_and_non_retryable() -> None:
    fixture = FixtureLanguageModel.from_path(QA_FIXTURES_ROOT / "grounded-qa-v1.json")
    changed = request().model_copy(update={"question": "What was promised?"})

    with pytest.raises(LanguageModelError) as raised:
        await fixture.answer(changed)
    assert raised.value.code == "provider_fixture_missing"
    assert raised.value.retry_class is RetryClass.NON_RETRYABLE


def test_fixture_reader_rejects_duplicates_and_unknown_fields(tmp_path: Path) -> None:
    original = json.loads((QA_FIXTURES_ROOT / "grounded-qa-v1.json").read_text(encoding="utf-8"))
    original["records"].append(original["records"][0])
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text(json.dumps(original), encoding="utf-8")
    with pytest.raises(ValueError, match="duplicates"):
        FixtureLanguageModel.from_path(duplicate)

    original["records"].pop()
    original["unexpected"] = True
    unknown = tmp_path / "unknown.json"
    unknown.write_text(json.dumps(original), encoding="utf-8")
    with pytest.raises(ValueError, match="invalid shape"):
        FixtureLanguageModel.from_path(unknown)


def test_structured_schema_is_closed_at_every_object_boundary() -> None:
    schema = structured_answer_schema()
    assert schema["additionalProperties"] is False
    definitions = cast(dict[str, dict[str, object]], schema["$defs"])
    assert all(value["additionalProperties"] is False for value in definitions.values())
