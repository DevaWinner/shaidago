"""Seed the demo database: ``python -m shaidago.seed`` (``make seed-demo``).

Reads ``DATABASE_URL`` (the migration owner) and ``APP_ENV``. Validates the source register and
every target check before opening a transaction, applies the plan in one transaction, and prints
what was added, updated, or left unchanged plus the evidence gaps. Refuses non-local and
staging or production targets.
"""

import asyncio
import os
import sys
from collections.abc import Mapping
from pathlib import Path

from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

from shaidago.retrieval.corpus import CorpusBuilder
from shaidago.retrieval.embeddings import embedding_path, load_embeddings
from shaidago.seed.apply import SeedRefusedError, apply_plan, assert_safe_target
from shaidago.seed.plan import REGISTER_PATH, RegisterInvalidError, build_plan, load_register
from shaidago.shared.clock import SystemClock
from shaidago.shared.database import Database, build_engine
from shaidago.shared.ids import Uuid7Generator


async def run(environ: Mapping[str, str], register_path: Path = REGISTER_PATH) -> str:
    try:
        url = make_url(environ.get("DATABASE_URL", ""))
    except ArgumentError:
        raise SeedRefusedError("DATABASE_URL is not a valid database URL") from None
    assert_safe_target(environ, url)
    plan = build_plan(load_register(register_path))  # validated before any connection is opened
    engine = build_engine(url, application_name="seed-demo", statement_timeout_ms=30_000)
    clock = SystemClock()
    ids = Uuid7Generator(clock)
    embedding_model = environ.get("EMBEDDING_MODEL", "text-embedding-3-small")
    checked_in = embedding_path(embedding_model)
    try:
        async with Database(engine).unit_of_work() as session:
            report = await apply_plan(session, plan, clock=clock, ids=ids)
            corpus = await CorpusBuilder(session, clock=clock, ids=ids).refresh()
            loaded = (
                await load_embeddings(
                    session,
                    checked_in,
                    expected_model=embedding_model,
                    now=clock.now(),
                )
                if checked_in.exists()
                else None
            )
    finally:
        await engine.dispose()
    corpus_line = (
        f"chunks: inserted {corpus.inserted}, refreshed {corpus.reactivated_or_changed}, "
        f"unchanged {corpus.unchanged}, deactivated {corpus.deactivated}\n"
    )
    embedding_line = (
        f"embeddings: loaded {loaded.matched_chunks} chunks from {loaded.records} records\n"
        if loaded is not None
        else f"embeddings: no checked-in file for {embedding_model}; keyword fallback enabled\n"
    )
    return report.render() + corpus_line + embedding_line


def main() -> int:
    try:
        sys.stdout.write(asyncio.run(run(os.environ)))
    except (SeedRefusedError, RegisterInvalidError) as error:
        sys.stderr.write(f"seed-demo: {error}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
