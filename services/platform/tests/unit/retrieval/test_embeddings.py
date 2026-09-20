import hashlib
from collections.abc import Sequence
from pathlib import Path

import pytest

from shaidago.retrieval.embeddings import (
    EMBEDDINGS_ROOT,
    EmbeddingRecord,
    embedding_path,
    generate_records,
    read_embedding_file,
    write_embedding_file,
)
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


def test_a_hub_model_id_maps_to_one_flat_file_and_never_a_folder() -> None:
    path = embedding_path("intfloat/multilingual-e5-large")
    assert path == EMBEDDINGS_ROOT / "intfloat__multilingual-e5-large.jsonl"
    assert path.parent == EMBEDDINGS_ROOT


@pytest.mark.parametrize(
    "model", ["", "../escape", "a/../b", "with space", "semi;colon", "x" * 200]
)
def test_an_unsafe_model_id_is_refused_as_a_file_name(model: str) -> None:
    with pytest.raises(ValueError, match="not safe as a file name"):
        embedding_path(model)


def test_the_checked_in_local_model_vectors_match_the_column_width() -> None:
    """The vectors `make seed-demo` loads must fit the vector(1024) column exactly."""
    path = embedding_path("intfloat/multilingual-e5-large")
    records = read_embedding_file(path, expected_model="intfloat/multilingual-e5-large")
    assert records, "run `make embeddings` after changing approved chunks"
    for record in records:
        assert len(record.embedding) == EMBEDDING_DIMENSIONS
        assert abs(sum(v * v for v in record.embedding) - 1.0) < 1e-3, "vectors are unit length"
