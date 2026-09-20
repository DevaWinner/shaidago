"""Explicit embedding generation: ``make embeddings``. Never imported by seed or request paths.

Embeds every approved public chunk with the local model (ADR-0010) and writes the checked-in file
that ``make seed-demo`` loads. It needs the downloaded model (``make embedding-model``) but no
provider key, no network, and no cost. The output is keyed by the SHA-256 of each chunk's exact
text, so a changed chunk simply has no vector until this command is run again.
"""

import asyncio
import os
import sys
from collections.abc import Mapping
from pathlib import Path

from sqlalchemy import text

from shaidago.retrieval.embeddings import (
    EmbeddingUnavailableError,
    embedding_path,
    generate_records,
    write_embedding_file,
)
from shaidago.retrieval.local_embeddings import FastEmbedModel
from shaidago.shared.config import ConfigurationError, load_settings
from shaidago.shared.database import Database, create_engine

_CHUNKS = text(
    "SELECT DISTINCT text_sha256, content_text FROM public_api.source_chunks ORDER BY text_sha256"
)


async def run(environ: Mapping[str, str], *, output: Path | None = None) -> str:
    settings = load_settings(environ)
    model_path = settings.providers.embedding_model_path
    if model_path is None:
        raise ConfigurationError(
            ["EMBEDDING_MODEL_PATH: required for embedding generation (run `make embedding-model`)"]
        )
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
    model = FastEmbedModel(model_path, threads=settings.providers.embedding_threads)
    await model.open()
    try:
        if not model.available:
            raise ConfigurationError(["EMBEDDING_MODEL_PATH: the model could not be loaded"])
        records = await generate_records(chunks, model)
    finally:
        await model.close()
    target = output or embedding_path(model.model_id)
    write_embedding_file(target, records)
    return f"embeddings: wrote {len(records)} records to {target}\n"


def main() -> int:
    try:
        sys.stdout.write(asyncio.run(run(os.environ)))
    except (ConfigurationError, ValueError, EmbeddingUnavailableError) as error:
        sys.stderr.write(f"embeddings: {error}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
