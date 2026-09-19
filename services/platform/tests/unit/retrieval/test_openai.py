import json
from datetime import UTC, datetime
from typing import cast

import httpx
import pytest

from shaidago.retrieval.language import (
    EvidencePassage,
    GroundedAnswerRequest,
    LanguageModelError,
    RetryClass,
    generated_at_text,
)
from shaidago.retrieval.openai import MAX_RESPONSE_BYTES, OpenAILanguageModel

NOW = datetime(2026, 9, 19, 17, 0, tzinfo=UTC)


def request() -> GroundedAnswerRequest:
    return GroundedAnswerRequest(
        locale="en",
        question="What does the approved source say?",
        passages=(
            EvidencePassage(
                citation_id="c_synthetic01",
                text="The synthetic clinic opened on 1 March.",
            ),
        ),
        generated_at=NOW,
    )


def answer_text(*, generated_at: str | None = None) -> str:
    return json.dumps(
        {
            "answer": "The synthetic clinic opened on 1 March.",
            "statements": [
                {
                    "text": "The synthetic clinic opened on 1 March.",
                    "citation_ids": ["c_synthetic01"],
                }
            ],
            "insufficient_evidence": False,
            "confidence_note": "The supplied passage covers the opening date only.",
            "generated_at": generated_at or generated_at_text(NOW),
        }
    )


def response_body(text: str | None = None) -> dict[str, object]:
    return {
        "status": "completed",
        "output": [
            {"type": "reasoning"},
            {
                "type": "message",
                "content": [{"type": "output_text", "text": text or answer_text()}],
            },
        ],
    }


async def call_with(handler: httpx.MockTransport) -> tuple[OpenAILanguageModel, httpx.AsyncClient]:
    client = httpx.AsyncClient(transport=handler, base_url="https://api.test")
    return (
        OpenAILanguageModel(api_key="secret-canary", model_id="configured-model", client=client),
        client,
    )


async def test_request_uses_responses_strict_schema_no_tools_and_no_storage(
    caplog: pytest.LogCaptureFixture,
) -> None:
    captured: dict[str, object] = {}

    def respond(http_request: httpx.Request) -> httpx.Response:
        captured["authorization"] = http_request.headers.get("Authorization")
        captured["body"] = json.loads(http_request.content)
        return httpx.Response(200, json=response_body())

    provider, client = await call_with(httpx.MockTransport(respond))
    try:
        result = await provider.answer(request())
    finally:
        await client.aclose()

    captured_body = captured["body"]
    assert isinstance(captured_body, dict)
    body = cast(dict[str, object], captured_body)
    assert captured["authorization"] == "Bearer secret-canary"
    assert set(body) == {
        "input",
        "instructions",
        "max_output_tokens",
        "model",
        "parallel_tool_calls",
        "store",
        "text",
        "tools",
    }
    assert body["model"] == "configured-model"
    assert body["store"] is False
    assert body["tools"] == []
    assert body["parallel_tool_calls"] is False
    assert body["max_output_tokens"] == 1200
    text_config = cast(dict[str, object], body["text"])
    output_format = cast(dict[str, object], text_config["format"])
    assert output_format["type"] == "json_schema"
    assert output_format["strict"] is True
    provider_input_value = body["input"]
    assert isinstance(provider_input_value, str)
    provider_payload = json.loads(provider_input_value)
    assert set(provider_payload) == {"generated_at", "locale", "passages", "question"}
    assert result.demo_replay is False
    assert result.answer.generated_at == NOW
    assert "What does the approved source say?" not in caplog.text
    assert "The synthetic clinic opened" not in caplog.text


@pytest.mark.parametrize("status", [408, 409, 429, 500, 503])
async def test_retryable_http_failures_are_classified_without_reading_or_leaking_body(
    status: int,
) -> None:
    calls = 0

    def respond(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(status, text="private-upstream-canary")

    provider, client = await call_with(httpx.MockTransport(respond))
    try:
        with pytest.raises(LanguageModelError) as raised:
            await provider.answer(request())
    finally:
        await client.aclose()
    assert raised.value.retry_class is RetryClass.RETRYABLE
    assert "private-upstream-canary" not in str(raised.value)
    assert calls == 1


@pytest.mark.parametrize("status", [400, 401, 403, 404, 422])
async def test_request_failures_are_non_retryable_and_safe(status: int) -> None:
    def respond(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, text="credential-or-prompt-canary")

    provider, client = await call_with(httpx.MockTransport(respond))
    try:
        with pytest.raises(LanguageModelError) as raised:
            await provider.answer(request())
    finally:
        await client.aclose()
    assert raised.value.retry_class is RetryClass.NON_RETRYABLE
    assert str(raised.value) == "provider_request_rejected"


async def test_timeout_is_retryable_but_not_retried_in_the_adapter() -> None:
    calls = 0

    def respond(http_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ReadTimeout("prompt canary", request=http_request)

    provider, client = await call_with(httpx.MockTransport(respond))
    try:
        with pytest.raises(LanguageModelError) as raised:
            await provider.answer(request())
    finally:
        await client.aclose()
    assert raised.value.retry_class is RetryClass.RETRYABLE
    assert str(raised.value) == "provider_timeout"
    assert calls == 1


@pytest.mark.parametrize(
    ("body", "code"),
    [
        (
            {
                "status": "completed",
                "output": [{"type": "message", "content": [{"type": "refusal"}]}],
            },
            "provider_refusal",
        ),
        (
            {"status": "completed", "output": [{"type": "function_call"}]},
            "provider_added_action",
        ),
    ],
)
async def test_refusal_or_provider_added_action_is_a_policy_failure(
    body: dict[str, object], code: str
) -> None:
    provider, client = await call_with(
        httpx.MockTransport(lambda _request: httpx.Response(200, json=body))
    )
    try:
        with pytest.raises(LanguageModelError) as raised:
            await provider.answer(request())
    finally:
        await client.aclose()
    assert raised.value.retry_class is RetryClass.POLICY_FAILURE
    assert raised.value.code == code


async def test_malformed_schema_and_application_timestamp_mismatch_are_non_retryable() -> None:
    bad_timestamp = answer_text(generated_at="2026-09-19T17:00:01.000000Z")
    responses = iter([response_body("{}"), response_body(bad_timestamp)])
    provider, client = await call_with(
        httpx.MockTransport(lambda _request: httpx.Response(200, json=next(responses)))
    )
    try:
        for code in ("provider_invalid_schema", "provider_invalid_timestamp"):
            with pytest.raises(LanguageModelError) as raised:
                await provider.answer(request())
            assert raised.value.retry_class is RetryClass.NON_RETRYABLE
            assert raised.value.code == code
    finally:
        await client.aclose()


async def test_response_body_is_bounded_before_json_parsing() -> None:
    provider, client = await call_with(
        httpx.MockTransport(
            lambda _request: httpx.Response(200, content=b"x" * (MAX_RESPONSE_BYTES + 1))
        )
    )
    try:
        with pytest.raises(LanguageModelError) as raised:
            await provider.answer(request())
    finally:
        await client.aclose()
    assert raised.value.code == "provider_response_too_large"
    assert raised.value.retry_class is RetryClass.NON_RETRYABLE


def test_timeout_is_bounded() -> None:
    with pytest.raises(ValueError, match="timeout"):
        OpenAILanguageModel(api_key="key", model_id="model", timeout_seconds=61)
