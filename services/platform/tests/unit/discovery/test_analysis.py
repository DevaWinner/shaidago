"""Discovery analysis: strict schema, deterministic validation, fail-closed to needs_review."""

import json
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest

from shaidago.discovery.analysis import (
    MAX_QUESTIONS,
    AnalysisInvalidError,
    AnalysisRequest,
    FixtureAnalyser,
    OpenAIAnalyser,
    SourcePassage,
    analyse_sources,
    analysis_schema,
    provider_input,
    request_fingerprint,
    validate_analysis,
)
from shaidago.retrieval.language import LanguageModelError
from shaidago.retrieval.openai import OpenAILanguageModel
from shaidago.review.private_references import PrivateContext

NOW = datetime(2026, 9, 19, 12, 0, tzinfo=UTC)
GEN = "2026-09-19T12:00:00Z"
A = SourcePassage(
    citation_id="s_aaaaaaaa1",
    publisher_domain="works.example.gov.ng",
    text="The clinic works contract was awarded on 1 March 2026 for 120 million naira.",
)
B = SourcePassage(
    citation_id="s_bbbbbbbb1",
    publisher_domain="news.example.org",
    text="A report says the clinic works were awarded in April 2026 for 90 million naira.",
)
REQUEST = AnalysisRequest(passages=(A, B), generated_at=NOW)


def good() -> dict[str, Any]:
    return {
        "summary": "Two public pages describe the clinic works contract.",
        "supported_facts": [
            {
                "text": "The clinic works contract was awarded on 1 March 2026",
                "citation_ids": [A.citation_id],
            }
        ],
        "reported_claims": [
            {
                "publisher": "news.example.org",
                "claim": "the clinic works were awarded in April 2026",
                "citation_id": B.citation_id,
            }
        ],
        "contradictions": [
            {
                "description": "The two pages give different award dates and amounts.",
                "citation_ids": [A.citation_id, B.citation_id],
            }
        ],
        "information_gaps": ["Neither page names the completion date."],
        "follow_up_questions": [
            {
                "question": "Is there a published contract award notice?",
                "reason": "Dates differ between sources.",
                "sensitivity": "low",
            }
        ],
        "safety_note": "Nothing here has been reviewed.",
        "confidence_note": "Two public pages were read; coverage is limited.",
        "generated_at": GEN,
    }


def check(payload: dict[str, Any], private: PrivateContext | None = None) -> None:
    validate_analysis(json.dumps(payload), REQUEST, private)


def code_of(payload: dict[str, Any] | str, private: PrivateContext | None = None) -> str:
    raw = payload if isinstance(payload, str) else json.dumps(payload)
    with pytest.raises(AnalysisInvalidError) as raised:
        validate_analysis(raw, REQUEST, private)
    return raised.value.code


def test_a_supported_attributed_analysis_validates() -> None:
    check(good())
    assert len(analysis_schema()["properties"]) == 9  # type: ignore[arg-type]


def mutate(**changes: Any) -> dict[str, Any]:
    return good() | changes


@pytest.mark.parametrize(
    ("payload", "code"),
    [
        ("not json", "malformed_schema"),
        (json.dumps({"summary": "x"}), "malformed_schema"),
        (mutate(extra="field"), "malformed_schema"),
        (mutate(generated_at="2026-09-19T12:00:01Z"), "timestamp_mismatch"),
        (
            mutate(
                supported_facts=[
                    {
                        "text": "The clinic works contract was awarded on 1 March 2026",
                        "citation_ids": ["s_unknown01"],
                    }
                ]
            ),
            "unknown_citation",
        ),
        (
            mutate(
                supported_facts=[
                    {
                        "text": "The clinic works contract was awarded on 1 March 2026",
                        "citation_ids": [A.citation_id, A.citation_id],
                    }
                ]
            ),
            "duplicate_citation",
        ),
        (
            mutate(
                supported_facts=[
                    {
                        "text": "The clinic works contract was awarded on 1 March 2026",
                        "citation_ids": [],
                    }
                ]
            ),
            "malformed_schema",
        ),
        (
            mutate(
                supported_facts=[
                    {
                        "text": "The clinic works contract was awarded on 2 March 2026",
                        "citation_ids": [A.citation_id],
                    }
                ]
            ),
            "unsupported_fact",
        ),
        (
            mutate(
                supported_facts=[
                    {
                        "text": "The contract was worth 500 million naira in total",
                        "citation_ids": [A.citation_id],
                    }
                ]
            ),
            "unsupported_fact",
        ),
        (
            mutate(
                reported_claims=[
                    {
                        "publisher": "works.example.gov.ng",
                        "claim": "the clinic works were awarded in April 2026",
                        "citation_id": B.citation_id,
                    }
                ]
            ),
            "misattributed_claim",
        ),
        (
            mutate(
                reported_claims=[
                    {
                        "publisher": "news.example.org",
                        "claim": "the works were finished last week entirely",
                        "citation_id": B.citation_id,
                    }
                ]
            ),
            "unsupported_claim",
        ),
        (
            mutate(
                contradictions=[
                    {"description": "Dates differ.", "citation_ids": [A.citation_id, A.citation_id]}
                ]
            ),
            "duplicate_citation",
        ),
        (
            mutate(
                follow_up_questions=[
                    {"question": f"Question number {n}?", "reason": "r", "sensitivity": "low"}
                    for n in range(MAX_QUESTIONS + 1)
                ]
            ),
            "too_many_questions",
        ),
        (
            mutate(
                follow_up_questions=[
                    {"question": "What is your phone number?", "reason": "r", "sensitivity": "high"}
                ]
            ),
            "unsafe_text",
        ),
        (
            mutate(
                follow_up_questions=[
                    {
                        "question": "Who is the contractor's manager?",
                        "reason": "r",
                        "sensitivity": "low",
                    }
                ]
            ),
            "question_requests_personal_data",
        ),
        (
            mutate(
                follow_up_questions=[
                    {
                        "question": "Can you share their home address?",
                        "reason": "r",
                        "sensitivity": "high",
                    }
                ]
            ),
            "question_requests_personal_data",
        ),
        (mutate(summary="The contractor is guilty of fraud."), "unsafe_text"),
        (mutate(summary="Mr Adeyemi ran the project."), "unsafe_text"),
        (mutate(summary="This proves the contract was corrupt."), "unsafe_text"),
        (mutate(confidence_note="We are 95% sure."), "unsafe_text"),
        (mutate(summary="Contact fictional@example.test for details."), "unsafe_text"),
        (mutate(information_gaps=["Call 0801 234 5678."]), "unsafe_text"),
        (mutate(safety_note="Send me your password."), "unsafe_text"),
    ],
)
def test_every_kind_of_invalid_analysis_is_refused_with_a_stable_code(
    payload: dict[str, Any] | str, code: str
) -> None:
    assert code_of(payload) == code


def test_a_contradiction_must_span_two_different_publishers() -> None:
    same = SourcePassage(
        citation_id="s_cccccccc1", publisher_domain="works.example.gov.ng", text=B.text
    )
    request = AnalysisRequest(passages=(A, same), generated_at=NOW)
    payload = good() | {
        "contradictions": [
            {"description": "They differ.", "citation_ids": [A.citation_id, same.citation_id]}
        ],
        "reported_claims": [],
    }
    with pytest.raises(AnalysisInvalidError) as raised:
        validate_analysis(json.dumps(payload), request)
    assert raised.value.code == "contradiction_needs_two_sources"


def test_private_terms_and_copied_report_text_are_refused() -> None:
    private = PrivateContext(
        texts=("FICTIONAL private text: the fictional supervisor demanded a fictional payment.",),
        contact_values=("private.person@example.test",),
        reviewer_names=("rev-abc123",),
    )
    check(good(), private)
    assert (
        code_of(
            mutate(summary="The fictional supervisor demanded a fictional payment, it says."),
            private,
        )
        == "private_term"
    )
    assert code_of(mutate(information_gaps=["Checked by rev-abc123."]), private) == "private_term"


def test_the_request_to_the_provider_carries_only_ids_publishers_and_excerpts() -> None:
    payload = json.loads(provider_input(REQUEST))
    assert set(payload) == {"generated_at", "passages"}
    assert all(set(p) == {"citation_id", "publisher", "text"} for p in payload["passages"])
    assert request_fingerprint(REQUEST) == request_fingerprint(REQUEST)
    other = AnalysisRequest(passages=(B, A), generated_at=NOW)
    assert request_fingerprint(other) != request_fingerprint(REQUEST)


async def test_valid_fixture_output_completes_and_is_labelled_a_replay() -> None:
    provider = FixtureAnalyser(
        {request_fingerprint(REQUEST): json.dumps(good() | {"generated_at": "stale"})}
    )
    outcome = await analyse_sources(provider, (A, B), NOW)
    assert (outcome.status, outcome.failure_code, outcome.demo_replay) == ("complete", None, True)
    assert outcome.analysis is not None
    assert outcome.analysis.generated_at == GEN


async def test_invalid_output_becomes_needs_review_and_carries_no_model_text() -> None:
    bad = good() | {"summary": "The contractor is guilty of fraud."}
    provider = FixtureAnalyser({request_fingerprint(REQUEST): json.dumps(bad)})
    outcome = await analyse_sources(provider, (A, B), NOW)
    assert (outcome.status, outcome.analysis, outcome.failure_code) == (
        "needs_review",
        None,
        "unsafe_text",
    )
    assert "guilty" not in repr(outcome)


async def test_a_missing_fixture_is_a_provider_error_not_a_guess() -> None:
    with pytest.raises(LanguageModelError):
        await analyse_sources(FixtureAnalyser({}), (A, B), NOW)


async def test_the_openai_analyser_sends_a_strict_toolless_unstored_request() -> None:
    seen: list[dict[str, Any]] = []

    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        output = {
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": json.dumps(good())}],
                }
            ],
        }
        return httpx.Response(200, json=output)

    client = httpx.AsyncClient(
        base_url="https://api.openai.com", transport=httpx.MockTransport(handle)
    )
    transport = OpenAILanguageModel(api_key="openai-key-canary", model_id="ignored", client=client)
    outcome = await analyse_sources(OpenAIAnalyser(transport, "model-x"), (A, B), NOW)
    [body] = seen
    assert (outcome.status, outcome.demo_replay, outcome.model_id) == ("complete", False, "model-x")
    assert body["store"] is False
    assert body["tools"] == []
    assert body["parallel_tool_calls"] is False
    assert body["text"]["format"]["strict"] is True
    assert body["model"] == "model-x"
    assert "openai-key-canary" not in json.dumps(body)
    assert json.loads(body["input"])["passages"][0]["citation_id"] == A.citation_id
