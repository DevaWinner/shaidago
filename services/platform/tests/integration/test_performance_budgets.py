"""Declared performance and resource budgets, measured on scaled synthetic data (BE-104).

Budgets are written in ``docs/PERFORMANCE_BUDGETS.md`` before any measurement and are deliberately
generous multiples of what a laptop achieves; they exist to catch an N+1, a missing index, or an
unbounded response, not to rank hardware. The measured numbers are kept in
``docs/evidence/BE-104-performance.md``. Run with ``-s`` to print them.
"""

import statistics
import time
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import event, text

from shaidago.auth.passwords import PasswordVerifier
from shaidago.files.rules import FileLimits
from shaidago.retrieval.chunking import MAX_CHUNK_CHARS
from shaidago.shared.config import DatabaseSettings, ObservabilitySettings
from shaidago.shared.vocabulary import values
from shaidago.worker.broker import MAX_RETRIES, TIME_LIMIT_MS
from tests.integration.reviewer_support import Actor, ReviewWorld
from tests.integration.support import LOCALITY

PROJECTS = 600
REPORTS = 600
SAMPLES = 120
BUDGET = {
    "public_list_p95_s": 0.150,
    "public_detail_p95_s": 0.150,
    "reviewer_queue_p95_s": 0.250,
    "reviewer_detail_p95_s": 0.300,
    "tracking_p95_s": 0.600,  # includes the intentional 0.25 s equalisation floor
    "public_list_bytes": 60_000,
    "reviewer_queue_bytes": 40_000,
    "reviewer_detail_bytes": 60_000,
    "public_list_statements": 4,
    "public_detail_statements": 12,
    "reviewer_queue_statements": 6,
    "reviewer_detail_statements": 16,
}
NOW = datetime(2026, 9, 19, 12, 0, tzinfo=UTC)


async def scale_data(world: ReviewWorld) -> None:
    prefix = f"perf-{uuid.uuid4().hex[:8]}-"
    key_id = uuid.uuid4()
    categories = list(values("project_category"))
    async with world.owner.unit_of_work() as session:
        await session.execute(
            text(
                "INSERT INTO app.projects SELECT gen_random_uuid(), :prefix || n, :loc, "
                "(CAST(:cats AS text[]))[1 + n % :ncat], 'planned', 'public', NULL, :now, :now "
                "FROM generate_series(1, :n) AS n"
            ),
            {
                "prefix": prefix,
                "loc": LOCALITY,
                "now": NOW,
                "n": PROJECTS,
                "cats": categories,
                "ncat": len(categories),
            },
        )
        await session.execute(
            text(
                "INSERT INTO app.project_translations SELECT gen_random_uuid(), id, 'en', 'Perf project ' || slug, "
                "'A synthetic performance-test summary of the works.', 'Synthetic deliverable', 'reviewed', :now, NULL, :now, :now "
                "FROM app.projects WHERE slug LIKE :like"
            ),
            {"now": NOW, "like": prefix + "%"},
        )
        await session.execute(
            text(
                "INSERT INTO app.data_keys (id, purpose, owner_table, owner_id, wrapped_key, kek_version, created_at) "
                "VALUES (:k, 'report_content', 'reports', gen_random_uuid(), decode(repeat('00', 60), 'hex'), 'kek-1', :now)"
            ),
            {"k": key_id, "now": NOW},
        )
        await session.execute(
            text(
                "INSERT INTO app.reports (id, project_id, concern_category, description_ciphertext, description_key_id, "
                "schema_version, risk_level, anonymous, status, status_updated_at, created_at, updated_at) "
                "SELECT gen_random_uuid(), p.id, 'no_visible_work', decode(repeat('00', 40), 'hex'), :k, 1, 'standard', true, "
                "'received', :now + n * interval '1 second', :now + n * interval '1 second', :now "
                "FROM (SELECT id, row_number() OVER () AS n FROM app.projects WHERE slug LIKE :like LIMIT :r) p"
            ),
            {"k": key_id, "now": NOW, "r": REPORTS, "like": prefix + "%"},
        )
        await session.execute(
            text(
                "INSERT INTO app.report_status_events (id, report_id, previous_status, new_status, public_message, actor_type, occurred_at) "
                "SELECT gen_random_uuid(), id, NULL, 'received', 'Received.', 'reporter', created_at FROM app.reports WHERE description_key_id = :k"
            ),
            {"k": key_id},
        )


class Counter:
    """Counts SQL statements issued through the given engines."""

    def __init__(self, world: ReviewWorld) -> None:
        deps = world.app.state.dependencies
        self.engines = [
            deps.public_database.engine.sync_engine,
            deps.reviewer_database.engine.sync_engine,
        ]
        self.count = 0
        for engine in self.engines:
            event.listen(engine, "before_cursor_execute", self._hit)

    def _hit(self, *_: object) -> None:
        self.count += 1

    def stop(self) -> None:
        for engine in self.engines:
            event.remove(engine, "before_cursor_execute", self._hit)


async def measure(
    world: ReviewWorld, actor: Actor | None, method: str, path: str, **kwargs: Any
) -> tuple[float, int, int]:
    """(p95 seconds, bytes of one response, SQL statements for one request)."""
    timings: list[float] = []
    size = 0
    counter = Counter(world)
    try:
        first = await world.call(actor, method, path, **kwargs)
        assert first.status_code == 200, (path, first.text[:200])
        statements, counter.count = counter.count, 0
        size = len(first.content)
        for _ in range(SAMPLES):
            started = time.perf_counter()
            response = await world.call(actor, method, path, **kwargs)
            timings.append(time.perf_counter() - started)
            assert response.status_code == 200
    finally:
        counter.stop()
    return statistics.quantiles(timings, n=20)[18], size, statements


async def test_endpoints_stay_within_their_declared_budgets_on_scaled_data(
    review_world: ReviewWorld,
) -> None:
    await scale_data(review_world)
    code, report_id = await review_world.submit(contact=True, attachments=1)
    actor = await review_world.signed_in()
    results: dict[str, tuple[float, int, int]] = {}
    results["public_list"] = await measure(
        review_world, None, "GET", "/v1/projects", params={"limit": 50}
    )
    results["public_detail"] = await measure(
        review_world, None, "GET", f"/v1/projects/{review_world.slug}"
    )
    results["reviewer_queue"] = await measure(
        review_world, actor, "GET", "/v1/reviewer/reports", params={"limit": 50}
    )
    results["reviewer_detail"] = await measure(
        review_world, actor, "GET", f"/v1/reviewer/reports/{report_id}"
    )
    tracking = await _tracking(review_world, code)
    for name, (p95, size, statements) in results.items():
        print(f"BUDGET {name}: p95={p95 * 1000:.1f} ms, bytes={size}, statements={statements}")  # noqa: T201
    print(f"BUDGET tracking: p95={tracking * 1000:.1f} ms")  # noqa: T201
    assert results["public_list"][0] < BUDGET["public_list_p95_s"]
    assert results["public_detail"][0] < BUDGET["public_detail_p95_s"]
    assert results["reviewer_queue"][0] < BUDGET["reviewer_queue_p95_s"]
    assert results["reviewer_detail"][0] < BUDGET["reviewer_detail_p95_s"]
    assert tracking < BUDGET["tracking_p95_s"]
    assert results["public_list"][1] < BUDGET["public_list_bytes"]
    assert results["reviewer_queue"][1] < BUDGET["reviewer_queue_bytes"]
    assert results["reviewer_detail"][1] < BUDGET["reviewer_detail_bytes"]
    assert results["public_list"][2] <= BUDGET["public_list_statements"]
    assert results["public_detail"][2] <= BUDGET["public_detail_statements"]
    assert results["reviewer_queue"][2] <= BUDGET["reviewer_queue_statements"]
    assert results["reviewer_detail"][2] <= BUDGET["reviewer_detail_statements"]


async def _tracking(world: ReviewWorld, code: str) -> float:
    timings: list[float] = []
    async with world.client() as http:
        for _ in range(20):
            started = time.perf_counter()
            response = await http.post(
                "/v1/report-status:lookup",
                json={"code": code},
                headers={
                    "X-Shaidago-Client-Hmac": uuid.uuid4().hex * 2
                },  # a fresh client each time
            )
            timings.append(time.perf_counter() - started)
            assert response.status_code == 200
    return statistics.quantiles(timings, n=20)[18]


async def test_statement_counts_do_not_grow_with_the_amount_of_data(
    review_world: ReviewWorld,
) -> None:
    actor = await review_world.signed_in()
    before = await measure_statements(review_world, actor)
    await scale_data(review_world)
    after = await measure_statements(review_world, actor)
    assert after == before  # 600 more projects and reports cost no extra statements


async def measure_statements(world: ReviewWorld, actor: Actor) -> dict[str, int]:
    counter = Counter(world)
    out: dict[str, int] = {}
    try:
        for name, (who, path) in {
            "list": (None, "/v1/projects?limit=50"),
            "queue": (actor, "/v1/reviewer/reports?limit=50"),
        }.items():
            counter.count = 0
            assert (await world.call(who, "GET", path)).status_code == 200
            out[name] = counter.count
    finally:
        counter.stop()
    return out


def test_resource_limits_are_within_their_declared_budgets() -> None:
    limits = FileLimits()
    assert (
        limits.max_file_bytes <= 10 * 1024 * 1024
    )  # one upload is spooled to disk, never held twice
    assert limits.max_pixels <= 25_000_000
    assert limits.max_pdf_pages <= 20
    assert (
        limits.sanitise_timeout_seconds + limits.scan_timeout_seconds + limits.store_timeout_seconds
        <= 60
    )
    assert MAX_CHUNK_CHARS <= 1000
    assert MAX_RETRIES <= 5
    assert TIME_LIMIT_MS <= 300_000


def test_pool_and_readiness_settings_are_bounded() -> None:
    database = DatabaseSettings.model_fields
    assert database["pool_size"].default <= 10
    assert database["statement_timeout_ms"].default <= 10_000
    assert database["connect_timeout_seconds"].default <= 10
    assert ObservabilitySettings.model_fields["readiness_timeout_seconds"].default <= 3


def test_one_production_strength_password_check_stays_under_half_a_second() -> None:
    verifier = PasswordVerifier()
    hashed = verifier.hash("a-long-enough-reviewer-password")
    started = time.perf_counter()
    assert verifier.verify(hashed, "a-long-enough-reviewer-password").matches
    assert time.perf_counter() - started < 0.5
