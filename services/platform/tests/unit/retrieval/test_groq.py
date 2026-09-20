import json
from datetime import UTC, datetime
from typing import cast

import httpx
import pytest

from shaidago.retrieval.groq import (
    CHAT_COMPLETIONS_PATH,
    MAX_RESPONSE_BYTES,
    GroqLanguageModel,
    wire_schema,
)
from shaidago.retrieval.language import (
    EvidencePassage,
    GroundedAnswerRequest,
    LanguageModelError,
    RetryClass,
    generated_at_text,
)

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


def answer_text(*, generated_at: str | None = None, locale: str = "en") -> str:
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
            "locale": locale,
        }
    )


def response_body(text: str | None = None) -> dict[str, object]:
    return {
        "choices": [
            {
                "finish_reason": "stop",
                "index": 0,
                "message": {"content": text or answer_text(), "role": "assistant"},
            }
        ]
    }


async def call_with(handler: httpx.MockTransport) -> tuple[GroqLanguageModel, httpx.AsyncClient]:
    client = httpx.AsyncClient(transport=handler, base_url="https://api.test")
    return (
        GroqLanguageModel(api_key="secret-canary", model_id="configured-model", client=client),
        client,
    )


async def test_request_uses_a_strict_schema_deterministic_decoding_and_no_tools(
    caplog: pytest.LogCaptureFixture,
) -> None:
    captured: dict[str, object] = {}

    def respond(http_request: httpx.Request) -> httpx.Response:
        captured["authorization"] = http_request.headers.get("Authorization")
        captured["path"] = http_request.url.path
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
    assert captured["path"] == CHAT_COMPLETIONS_PATH
    assert set(body) == {
        "max_completion_tokens",
        "messages",
        "model",
        "response_format",
        "stream",
        "temperature",
    }
    assert body["model"] == "configured-model"
    assert body["stream"] is False
    assert body["temperature"] == 0
    assert "tools" not in body  # the model is never offered an action
    assert body["max_completion_tokens"] == 1200
    response_format = cast(dict[str, object], body["response_format"])
    assert response_format["type"] == "json_schema"
    schema_config = cast(dict[str, object], response_format["json_schema"])
    assert schema_config["strict"] is True
    assert schema_config["name"] == "grounded_answer"
    messages = cast(list[object], body["messages"])
    system, user = (cast(dict[str, object], message) for message in messages)
    assert system["role"] == "system"
    assert user["role"] == "user"
    provider_input_value = user["content"]
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
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"content": None, "refusal": "I cannot help with that"},
                    }
                ]
            },
            "provider_refusal",
        ),
        (
            {
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"content": None, "tool_calls": [{"id": "call_1"}]},
                    }
                ]
            },
            "provider_added_action",
        ),
        (
            {"choices": [{"finish_reason": "tool_calls", "message": {"content": None}}]},
            "provider_incomplete",
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
    wrong_locale = answer_text(locale="ha")
    responses = iter(
        [response_body("{}"), response_body(bad_timestamp), response_body(wrong_locale)]
    )
    provider, client = await call_with(
        httpx.MockTransport(lambda _request: httpx.Response(200, json=next(responses)))
    )
    try:
        for code in (
            "provider_invalid_schema",
            "provider_invalid_timestamp",
            "provider_wrong_locale",
        ):
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
        GroqLanguageModel(api_key="key", model_id="model", timeout_seconds=61)


async def test_a_truncated_answer_is_not_retried() -> None:
    body = {"choices": [{"finish_reason": "length", "message": {"content": '{"answ'}}]}
    provider, client = await call_with(
        httpx.MockTransport(lambda _request: httpx.Response(200, json=body))
    )
    try:
        with pytest.raises(LanguageModelError) as raised:
            await provider.answer(request())
    finally:
        await client.aclose()
    assert raised.value.code == "provider_incomplete"
    assert raised.value.retry_class is RetryClass.NON_RETRYABLE


def test_the_wire_schema_drops_only_the_keyword_the_decoder_rejects() -> None:
    schema = {
        "$defs": {"Item": {"properties": {"id": {"pattern": "^c_[a-z0-9]+$", "type": "string"}}}},
        "additionalProperties": False,
        "properties": {
            "items": {"items": {"$ref": "#/$defs/Item"}, "maxItems": 8, "type": "array"},
            "note": {"maxLength": 500, "minLength": 1, "pattern": "^.+$", "type": "string"},
        },
    }
    wire = cast(dict[str, object], wire_schema(schema))
    assert "pattern" not in json.dumps(wire)
    properties = cast(dict[str, object], wire["properties"])
    note = cast(dict[str, object], properties["note"])
    assert note["maxLength"] == 500  # bounds the decoder accepts are kept
    assert note["minLength"] == 1
    definitions = cast(dict[str, object], wire["$defs"])
    item = cast(dict[str, object], definitions["Item"])
    item_properties = cast(dict[str, object], item["properties"])
    assert cast(dict[str, object], item_properties["id"])["type"] == "string"


async def test_a_citation_id_violating_the_pattern_still_fails_closed() -> None:
    # The wire schema cannot enforce the pattern, so the parser must.
    forged = json.loads(answer_text())
    forged["statements"][0]["citation_ids"] = ["NOT-A-CITATION-ID"]
    provider, client = await call_with(
        httpx.MockTransport(
            lambda _request: httpx.Response(200, json=response_body(json.dumps(forged)))
        )
    )
    try:
        with pytest.raises(LanguageModelError) as raised:
            await provider.answer(request())
    finally:
        await client.aclose()
    assert raised.value.retry_class is RetryClass.NON_RETRYABLE
    assert raised.value.code == "provider_invalid_schema"
