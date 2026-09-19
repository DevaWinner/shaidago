"""Search adapters (no network) and the public-run budget decision."""

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest

from shaidago.discovery.budget import BudgetDecision, PriorRun, decide_public_run
from shaidago.discovery.planner import UnsafeQueryError
from shaidago.discovery.search import (
    BraveSearchProvider,
    FixtureSearchProvider,
    SearchRejectedError,
    SearchUnavailableError,
    query_fingerprint,
)

KEY = "brave-key-canary-do-not-leak"
NOW = datetime(2026, 9, 19, 12, 0, tzinfo=UTC)


def brave(
    handler: httpx.MockTransport, attempts: int = 2
) -> tuple[BraveSearchProvider, list[float]]:
    sleeps: list[float] = []

    async def sleep(seconds: float) -> None:
        sleeps.append(seconds)

    client = httpx.AsyncClient(transport=handler)
    return BraveSearchProvider(KEY, client=client, max_attempts=attempts, sleep=sleep), sleeps


def ok(urls: list[object]) -> httpx.Response:
    return httpx.Response(
        200,
        json={"web": {"results": [{"url": u, "description": "SNIPPET", "rank": 1} for u in urls]}},
    )


async def test_a_request_carries_only_the_query_a_count_and_the_key() -> None:
    seen: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return ok(["https://example.test/a"])

    provider, _ = brave(httpx.MockTransport(handle))
    results = await provider.search("Synthetic Clinic 2026")
    [request] = seen
    assert request.url.params["q"] == "Synthetic Clinic 2026"
    assert request.url.params["count"] == "10"
    assert request.headers["x-subscription-token"] == KEY
    assert set(request.url.params) == {"q", "count", "safesearch"}
    assert (results.provider, results.demo_replay) == ("brave", False)
    assert results.urls == ("https://example.test/a",)
    assert not hasattr(results, "snippets")
    assert "SNIPPET" not in repr(results)


async def test_an_unsafe_query_is_refused_before_any_request_is_made() -> None:
    def handle(_request: httpx.Request) -> httpx.Response:  # pragma: no cover - must not run
        raise AssertionError("no request may be made")

    provider, _ = brave(httpx.MockTransport(handle))
    for query in ("clinic someone@example.test", "clinic 08012345678", ""):
        with pytest.raises(UnsafeQueryError):
            await provider.search(query)


async def test_results_are_capped_deduplicated_and_only_http_urls_survive() -> None:
    urls: list[object] = [f"https://example.test/{n}" for n in range(30)]
    urls[1] = urls[0]
    urls[2] = "javascript:alert(1)"
    urls[3] = "ftp://example.test/x"
    urls[4] = 5
    urls[5] = "https:///nohost"
    urls[6] = "https://example.test/" + "x" * 3000
    provider, _ = brave(httpx.MockTransport(lambda _r: ok(urls)))
    results = await provider.search("clinic")
    assert len(results.urls) == 10
    assert len(set(results.urls)) == 10
    assert all(u.startswith("https://example.test/") and len(u) < 100 for u in results.urls)


async def test_a_retryable_failure_is_retried_a_bounded_number_of_times() -> None:
    calls = {"n": 0}

    def flaky(_r: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(429) if calls["n"] == 1 else ok(["https://example.test/a"])

    provider, sleeps = brave(httpx.MockTransport(flaky))
    assert (await provider.search("clinic")).urls == ("https://example.test/a",)
    assert calls["n"] == 2
    assert sleeps == [0.5]
    down, sleeps2 = brave(httpx.MockTransport(lambda _r: httpx.Response(503)), attempts=3)
    with pytest.raises(SearchUnavailableError):
        await down.search("clinic")
    assert sleeps2 == [0.5, 1.0]


async def test_timeouts_and_connection_errors_are_retryable_and_leak_nothing() -> None:
    def timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    provider, _ = brave(httpx.MockTransport(timeout))
    with pytest.raises(SearchUnavailableError) as raised:
        await provider.search("Synthetic Clinic")
    assert KEY not in repr(raised.value)
    assert "Synthetic" not in repr(raised.value)


@pytest.mark.parametrize("status", [400, 401, 403, 404, 422])
async def test_a_client_error_is_not_retried(status: int) -> None:
    calls = {"n": 0}

    def refuse(_r: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(status)

    provider, _ = brave(httpx.MockTransport(refuse))
    with pytest.raises(SearchRejectedError):
        await provider.search("clinic")
    assert calls["n"] == 1


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, content=b"not json"),
        httpx.Response(200, json={"web": {}}),
        httpx.Response(200, json={"web": {"results": 5}}),
        httpx.Response(200, json=[]),
        httpx.Response(200, content=b"{" + b" " * 1_100_000 + b"}"),
    ],
)
async def test_malformed_or_oversized_responses_are_rejected(response: httpx.Response) -> None:
    provider, _ = brave(httpx.MockTransport(lambda _r: response))
    with pytest.raises(SearchRejectedError):
        await provider.search("clinic")


def test_the_credential_never_appears_in_a_repr() -> None:
    provider, _ = brave(httpx.MockTransport(lambda _r: httpx.Response(200)))
    assert KEY not in repr(provider)


def write_fixture(path: Path, entries: list[dict[str, object]]) -> Path:
    path.write_text(json.dumps({"fixture_version": 1, "entries": entries}), "utf-8")
    return path


async def test_the_fixture_provider_replays_by_fingerprint_and_labels_it(tmp_path: Path) -> None:
    fixture = write_fixture(
        tmp_path / "s.json",
        [
            {
                "query_sha256": query_fingerprint("Synthetic Clinic"),
                "urls": ["https://example.test/a", "ftp://x/y"],
            },
            {"query_sha256": query_fingerprint("outage"), "urls": [], "error": "unavailable"},
            {"query_sha256": query_fingerprint("refused"), "urls": [], "error": "rejected"},
        ],
    )
    provider = FixtureSearchProvider.from_file(fixture)
    results = await provider.search("  synthetic CLINIC ")
    assert results.urls == ("https://example.test/a",)
    assert (results.provider, results.demo_replay) == ("fixture", True)
    assert (await provider.search("unknown query")).urls == ()
    with pytest.raises(SearchUnavailableError):
        await provider.search("outage")
    with pytest.raises(SearchRejectedError):
        await provider.search("refused")
    with pytest.raises(UnsafeQueryError):
        await provider.search("clinic a@b.example")


def test_a_bad_fixture_file_is_refused(tmp_path: Path) -> None:
    for content in (
        "not json",
        '{"fixture_version": 2, "entries": []}',
        '{"fixture_version": 1, "entries": [{"query_sha256": "x"}]}',
    ):
        path = tmp_path / "bad.json"
        path.write_text(content, "utf-8")
        with pytest.raises(SearchRejectedError):
            FixtureSearchProvider.from_file(path)
    with pytest.raises(SearchRejectedError):
        FixtureSearchProvider.from_file(tmp_path / "missing.json")
    assert query_fingerprint("A") == hashlib.sha256(b"a").hexdigest()


def run(run_id: str, status: str, age_hours: float) -> PriorRun:
    created = NOW - timedelta(hours=age_hours)
    return PriorRun(run_id, status, created, created if status == "complete" else None)


def test_a_fresh_or_in_flight_run_is_reused_and_costs_nothing() -> None:
    fresh = decide_public_run(
        now=NOW, runs=[run("a", "complete", 3)], fresh_runs_today=99, daily_limit=20
    )
    assert fresh == BudgetDecision("reuse_fresh", "a")
    flying = decide_public_run(
        now=NOW, runs=[run("b", "searching", 30)], fresh_runs_today=99, daily_limit=20
    )
    assert flying == BudgetDecision("reuse_fresh", "b")
    review = decide_public_run(
        now=NOW, runs=[run("c", "needs_review", 30)], fresh_runs_today=99, daily_limit=20
    )
    assert review.action == "reuse_fresh"


def test_a_stale_or_failed_run_allows_a_new_one_while_budget_remains() -> None:
    runs = [run("f", "failed", 1), run("x", "cancelled", 2), run("old", "complete", 30)]
    assert decide_public_run(
        now=NOW, runs=runs, fresh_runs_today=19, daily_limit=20
    ) == BudgetDecision("create")
    assert (
        decide_public_run(now=NOW, runs=[], fresh_runs_today=0, daily_limit=20).action == "create"
    )


def test_an_exhausted_budget_shows_the_latest_completed_run_or_says_unavailable() -> None:
    runs = [run("f", "failed", 1), run("old", "complete", 30), run("older", "complete", 90)]
    assert decide_public_run(
        now=NOW, runs=runs, fresh_runs_today=20, daily_limit=20
    ) == BudgetDecision("show_latest_completed", "old")
    assert decide_public_run(
        now=NOW, runs=[run("f", "failed", 1)], fresh_runs_today=20, daily_limit=20
    ) == BudgetDecision("unavailable")
