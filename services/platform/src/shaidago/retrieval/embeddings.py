"""Checked-in embedding records and explicit generation interfaces.

Ordinary seed and request paths only load a reviewed JSONL file. They never contact a provider.
The explicit generation command is the only caller of an ``EmbeddingModel`` implementation.
"""

import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol, cast

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shaidago.retrieval.search import EMBEDDING_MODEL_MAX_CHARS, vector_literal

EMBEDDINGS_ROOT = Path(__file__).parents[5] / "data" / "embeddings"
FIXTURE_VERSION = 1
SHA256_HEX_CHARS = 64

_APPLY = text(
    "UPDATE app.source_chunks c SET embedding = CAST(:embedding AS vector), "
    "embedding_model = :model, embedded_at = :now, updated_at = :now "
    "WHERE c.active AND c.text_sha256 = :sha AND EXISTS ("
    "SELECT 1 FROM app.approved_source_documents d "
    "WHERE d.project_id = c.project_id AND d.source_id = c.source_id "
    "AND d.source_version_id = c.source_version_id AND d.language = c.language) "
    "RETURNING c.id"
)


class EmbeddingModel(Protocol):
    model_id: str

    async def embed(self, texts: Sequence[str]) -> Sequence[Sequence[float]]: ...


@dataclass(frozen=True)
class EmbeddingRecord:
    model: str
    text_sha256: str
    embedding: tuple[float, ...]


@dataclass(frozen=True)
class EmbeddingLoad:
    records: int
    matched_chunks: int
    unmatched_records: int


def embedding_path(model: str) -> Path:
    safe_characters = "-._0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    if (
        not model
        or len(model) > EMBEDDING_MODEL_MAX_CHARS
        or any(character not in safe_characters for character in model)
    ):
        raise ValueError("embedding model is not safe as a file name")
    return EMBEDDINGS_ROOT / f"{model}.jsonl"


def _record(value: object, *, line: int, expected_model: str) -> EmbeddingRecord:
    if not isinstance(value, dict):
        raise ValueError(f"embedding line {line} has an invalid shape")
    # JSON parsing and the runtime mapping check prove this is an object; keys are checked next.
    mapping = cast(dict[str, object], value)
    if set(mapping) != {
        "fixture_version",
        "model",
        "text_sha256",
        "embedding",
    }:
        raise ValueError(f"embedding line {line} has an invalid shape")
    if mapping["fixture_version"] != FIXTURE_VERSION:
        raise ValueError(f"embedding line {line} has an unsupported fixture version")
    model = mapping["model"]
    sha = mapping["text_sha256"]
    vector = mapping["embedding"]
    if not isinstance(model, str) or model != expected_model:
        raise ValueError(f"embedding line {line} has the wrong model")
    if (
        not isinstance(sha, str)
        or len(sha) != SHA256_HEX_CHARS
        or any(c not in "0123456789abcdef" for c in sha)
    ):
        raise ValueError(f"embedding line {line} has an invalid chunk hash")
    if not isinstance(vector, list):
        raise ValueError(f"embedding line {line} has an invalid vector")
    items = cast(list[object], vector)
    if any(isinstance(item, bool) or not isinstance(item, int | float) for item in items):
        raise ValueError(f"embedding line {line} has an invalid vector")
    floats = tuple(float(item) for item in items if isinstance(item, int | float))
    vector_literal(floats)  # checks dimension, finiteness, and bounded values
    return EmbeddingRecord(model=model, text_sha256=sha, embedding=floats)


def read_embedding_file(path: Path, *, expected_model: str) -> tuple[EmbeddingRecord, ...]:
    seen: set[str] = set()
    records: list[EmbeddingRecord] = []
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            loaded: object = json.loads(raw)
        except json.JSONDecodeError as error:
            raise ValueError(f"embedding line {line_number} is not valid JSON") from error
        record = _record(loaded, line=line_number, expected_model=expected_model)
        if record.text_sha256 in seen:
            raise ValueError(f"embedding line {line_number} duplicates a chunk hash")
        seen.add(record.text_sha256)
        records.append(record)
    return tuple(records)


async def load_embeddings(
    session: AsyncSession,
    path: Path,
    *,
    expected_model: str,
    now: datetime,
) -> EmbeddingLoad:
    records = read_embedding_file(path, expected_model=expected_model)
    matched = 0
    unmatched = 0
    for record in records:
        rows = (
            await session.execute(
                _APPLY,
                {
                    "embedding": vector_literal(record.embedding),
                    "model": record.model,
                    "sha": record.text_sha256,
                    "now": now,
                },
            )
        ).all()
        matched += len(rows)
        if not rows:
            unmatched += 1
    return EmbeddingLoad(
        records=len(records),
        matched_chunks=matched,
        unmatched_records=unmatched,
    )


async def generate_records(
    chunks: Sequence[tuple[str, str]], provider: EmbeddingModel
) -> tuple[EmbeddingRecord, ...]:
    """Generate records only when an explicit command supplies a provider."""
    if not chunks:
        return ()
    vectors = await provider.embed([content for _sha, content in chunks])
    if len(vectors) != len(chunks):
        raise ValueError("embedding provider returned the wrong number of vectors")
    records = tuple(
        EmbeddingRecord(
            model=provider.model_id,
            text_sha256=sha,
            embedding=tuple(float(value) for value in vector),
        )
        for (sha, _content), vector in zip(chunks, vectors, strict=True)
    )
    for record in records:
        vector_literal(record.embedding)
    return records


def write_embedding_file(path: Path, records: Sequence[EmbeddingRecord]) -> None:
    lines: list[str] = []
    for record in records:
        vector_literal(record.embedding)
        lines.append(
            json.dumps(
                {
                    "fixture_version": FIXTURE_VERSION,
                    "model": record.model,
                    "text_sha256": record.text_sha256,
                    "embedding": record.embedding,
                },
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    temporary.replace(path)
