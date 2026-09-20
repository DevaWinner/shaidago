"""Seed one fictional project for the staging smoke journey (BE-114).

Run as ``python -m shaidago.seed.staging_fixture``.

The smoke journey (``scripts/staging_smoke.py``, BE-114) publishes an update and runs Source Scout
from replay fixtures. Both need a project and an approved source version that are *not real*: the
recorded replays are keyed to a project titled "Fixture Scenario Success" in a locality called
"Synthetic Council", and publishing a test update onto a real project's public page would be wrong.

Everything here is labelled fictional in the data itself, uses the reserved ``.example`` domain, and
describes no real project, institution, contractor or person. It goes through the same audited
seed path as the register, so it is idempotent, and it refuses the same targets: local databases,
or ``APP_ENV=staging`` with ``SEED_ALLOW_DEPLOYED=1``. Production has no seed mode.
"""

import asyncio
import os
import sys
from collections.abc import Mapping
from datetime import UTC, date, datetime

from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

from shaidago.retrieval.corpus import CorpusBuilder
from shaidago.seed.apply import SeedRefusedError, apply_plan, assert_safe_target
from shaidago.seed.plan import (
    CitationPlan,
    FactPlan,
    LocalityPlan,
    ProjectPlan,
    SeedPlan,
    SourcePlan,
    TranslationPlan,
)
from shaidago.shared.clock import SystemClock
from shaidago.shared.database import Database, build_engine
from shaidago.shared.ids import Uuid7Generator

SLUG = "fixture-scenario-success"
TITLE = "Fixture Scenario Success"
LOCALITY_NAME = "Synthetic Council"
CATEGORY = "health"
# The recorded replay query is title, locality name and category, in that order.
REPLAY_QUERY = f"{TITLE} {LOCALITY_NAME} {CATEGORY}"

PASSAGE = "The synthetic clinic opened on 1 March."
DOCUMENT = f"Synthetic document. {PASSAGE} Section two follows."
FICTIONAL = "FICTIONAL staging fixture. It describes no real project, institution or person."
APPROVAL_NOTE = (
    "Synthetic staging fixture, not a real source: approved so the fictional smoke journey can "
    "cite it. Never seeded outside local or explicitly flagged staging databases."
)


def build_fixture_plan() -> SeedPlan:
    source_url = "https://synthetic.example/fixture-scenario-success"
    return SeedPlan(
        localities=[LocalityPlan("synthetic-council", LOCALITY_NAME, "area_council", None)],
        projects=[
            ProjectPlan(
                slug=SLUG,
                locality_slug="synthetic-council",
                category=CATEGORY,
                checked_on=date(2026, 9, 19),
                translations=(
                    TranslationPlan(
                        "en",
                        TITLE,
                        f"{FICTIONAL} It exists only to exercise the staging smoke journey.",
                        "",
                        "machine_assisted",
                    ),
                ),
            )
        ],
        sources=[
            SourcePlan(
                url=source_url,
                title="Synthetic source (fictional)",
                publisher="Synthetic Publisher (fictional)",
                source_type="government_publication",
                information_class="official_source",
                availability="available",
                checked_at=datetime(2026, 9, 19, 12, 0, tzinfo=UTC),
                content=DOCUMENT,
                approval_note=APPROVAL_NOTE,
            )
        ],
        facts=[
            FactPlan(
                project_slug=SLUG,
                kind="fixture_fact",
                statement=f"FICTIONAL: {PASSAGE}",
                citations=(CitationPlan(source_url, PASSAGE),),
            )
        ],
    )


async def run(environ: Mapping[str, str]) -> str:
    try:
        url = make_url(environ.get("DATABASE_URL", ""))
    except ArgumentError:
        raise SeedRefusedError("DATABASE_URL is not a valid database URL") from None
    assert_safe_target(environ, url)
    engine = build_engine(url, application_name="staging-fixture", statement_timeout_ms=30_000)
    clock = SystemClock()
    ids = Uuid7Generator(clock)
    try:
        async with Database(engine).unit_of_work() as session:
            report = await apply_plan(session, build_fixture_plan(), clock=clock, ids=ids)
            corpus = await CorpusBuilder(session, clock=clock, ids=ids).refresh()
    finally:
        await engine.dispose()
    return (
        f"fictional staging fixture '{SLUG}'\n{report.render()}chunks: inserted {corpus.inserted}\n"
    )


def main() -> int:
    try:
        sys.stdout.write(asyncio.run(run(os.environ)))
    except SeedRefusedError as error:
        sys.stderr.write(f"staging fixture: {error}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
