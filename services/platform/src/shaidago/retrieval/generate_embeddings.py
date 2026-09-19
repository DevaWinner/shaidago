"""Explicit embedding generation command; never imported by seed or request paths."""

import asyncio
import os
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict
from sqlalchemy import text

from shaidago.retrieval.embeddings import (
    EmbeddingModel,
    embedding_path,
    generate_records,
    write_embedding_file,
)
from shaidago.retrieval.search import EMBEDDING_DIMENSIONS
from shaidago.shared.config import ConfigurationError, load_settings
from shaidago.shared.database import Database, create_engine

_CHUNKS = text(
    "SELECT DISTINCT text_sha256, content_text FROM public_api.source_chunks ORDER BY text_sha256"
)
MAX_BATCH = 32


class _EmbeddingItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    index: int
    embedding: list[float]


class _EmbeddingResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    data: list[_EmbeddingItem]


class OpenAIEmbeddingModel(EmbeddingModel):
    """Minimal embeddings adapter used only by this explicit command."""

    def __init__(
        self,
        *,
        api_key: str,
        model_id: str,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.model_id = model_id
        self._authorization = f"Bearer {api_key}"
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            base_url="https://api.openai.com",
            timeout=httpx.Timeout(30.0, connect=5.0),
        )

    async def embed(self, texts: Sequence[str]) -> Sequence[Sequence[float]]:
        vectors: list[Sequence[float]] = []
        for offset in range(0, len(texts), MAX_BATCH):
            batch = list(texts[offset : offset + MAX_BATCH])
            response = await self._client.post(
                "/v1/embeddings",
                headers={"Authorization": self._authorization},
                json={
                    "model": self.model_id,
                    "input": batch,
                    "dimensions": EMBEDDING_DIMENSIONS,
                    "encoding_format": "float",
                },
            )
            response.raise_for_status()
            body: Any = response.json()
            parsed = _EmbeddingResponse.model_validate(body)
            ordered = sorted(parsed.data, key=lambda item: item.index)
            if [item.index for item in ordered] != list(range(len(batch))):
                raise ValueError("embedding provider returned invalid indexes")
            vectors.extend(item.embedding for item in ordered)
        return vectors

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()


async def run(
    environ: Mapping[str, str],
    *,
    output: Path | None = None,
    client: httpx.AsyncClient | None = None,
) -> str:
    settings = load_settings(environ)
    key = settings.providers.openai_api_key
    if key is None:
        raise ConfigurationError(["OPENAI_API_KEY: required for explicit embedding generation"])
    engine = create_engine(
        settings.database,
        application_name="generate-embeddings",
        url=settings.database.public_sqlalchemy_url(),
    )
    try:
        async with Database(engine).unit_of_work() as session:
            chunks = [tuple(row) for row in (await session.execute(_CHUNKS)).all()]
    finally:
        await engine.dispose()
    provider = OpenAIEmbeddingModel(
        api_key=key.get_secret_value(),
        model_id=settings.providers.embedding_model,
        client=client,
    )
    try:
        records = await generate_records(chunks, provider)
    finally:
        await provider.close()
    target = output or embedding_path(provider.model_id)
    write_embedding_file(target, records)
    return f"embeddings: wrote {len(records)} records to {target}\n"


def main() -> int:
    try:
        sys.stdout.write(asyncio.run(run(os.environ)))
    except (ConfigurationError, ValueError, httpx.HTTPError) as error:
        sys.stderr.write(f"embeddings: {error}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
