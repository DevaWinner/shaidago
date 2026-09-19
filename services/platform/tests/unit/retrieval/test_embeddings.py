import hashlib
from collections.abc import Sequence
from pathlib import Path

import httpx
import pytest

from shaidago.retrieval.embeddings import (
    EMBEDDINGS_ROOT,
    EmbeddingRecord,
    generate_records,
    read_embedding_file,
    write_embedding_file,
)
from shaidago.retrieval.generate_embeddings import OpenAIEmbeddingModel
from shaidago.retrieval.search import EMBEDDING_DIMENSIONS


class FixtureModel:
    model_id = "fixture-model"

    async def embed(self, texts: Sequence[str]) -> Sequence[Sequence[float]]:
        return [
            ([float(index + 1)] + [0.0] * (EMBEDDING_DIMENSIONS - 1)) for index in range(len(texts))
        ]


def test_checked_in_fixture_is_strict_and_carries_no_source_text() -> None:
    path = EMBEDDINGS_ROOT / "fixture-hash-v1.jsonl"
    records = read_embedding_file(path, expected_model="fixture-hash-v1")

    assert len(records) == 1
    assert len(records[0].embedding) == EMBEDDING_DIMENSIONS
    raw = path.read_text(encoding="utf-8")
    assert "Synthetic document" not in raw
    assert (
        records[0].text_sha256
        == hashlib.sha256(
            b"Synthetic document. The synthetic clinic opened on 1 March. Section two follows."
        ).hexdigest()
    )


async def test_generation_uses_the_supplied_explicit_provider_and_round_trips(
    tmp_path: Path,
) -> None:
    chunks = (("a" * 64, "first public chunk"), ("b" * 64, "second public chunk"))
    records = await generate_records(chunks, FixtureModel())
    path = tmp_path / "fixture-model.jsonl"
    write_embedding_file(path, records)

    assert read_embedding_file(path, expected_model="fixture-model") == records


def test_reader_rejects_unknown_fields_duplicate_hashes_and_wrong_dimensions(
    tmp_path: Path,
) -> None:
    valid = EmbeddingRecord("fixture-model", "a" * 64, (0.0,) * EMBEDDING_DIMENSIONS)
    path = tmp_path / "bad.jsonl"
    write_embedding_file(path, [valid, valid])
    with pytest.raises(ValueError, match="duplicates"):
        read_embedding_file(path, expected_model="fixture-model")

    path.write_text(
        '{"fixture_version":1,"model":"fixture-model","text_sha256":"'
        + "a" * 64
        + '","embedding":[0],"extra":true}\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="shape"):
        read_embedding_file(path, expected_model="fixture-model")


async def test_openai_embedding_adapter_sends_only_bounded_explicit_inputs() -> None:
    captured: dict[str, object] = {}

    def respond(request: httpx.Request) -> httpx.Response:
        captured["authorization"] = request.headers.get("Authorization")
        captured["body"] = request.content.decode()
        return httpx.Response(
            200,
            json={"data": [{"index": 0, "embedding": [1.0] + [0.0] * (EMBEDDING_DIMENSIONS - 1)}]},
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(respond), base_url="https://api.test")
    provider = OpenAIEmbeddingModel(
        api_key="secret-canary", model_id="fixture-model", client=client
    )
    try:
        vectors = await provider.embed(["approved public chunk"])
    finally:
        await client.aclose()

    assert len(vectors[0]) == EMBEDDING_DIMENSIONS
    assert captured["authorization"] == "Bearer secret-canary"
    assert "approved public chunk" in str(captured["body"])
