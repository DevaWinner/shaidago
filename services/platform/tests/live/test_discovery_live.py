"""Opt-in live check of the search adapter (ADR-0008). Never run in CI or by ``make verify``.

    SHAIDAGO_LIVE_TESTS=1 SEARCH_API_KEY=... LIVE_PROJECT_TITLE="<a public project title>" \
        uv run pytest tests/live -m live

It sends only the planner's allowlisted query for a public project title and asserts the shape
of the result. It prints counts, never the key or the raw response. The maintainer records the
outcome by hand in ``docs/evidence/BE-097-live-evidence.md`` after reviewing the URLs.
"""

import os

import httpx
import pytest

from shaidago.discovery.planner import PublicProjectTerms, plan_public_query
from shaidago.discovery.search import MAX_RESULTS, BraveSearchProvider

pytestmark = pytest.mark.live
ENABLED = os.environ.get("SHAIDAGO_LIVE_TESTS") == "1"


@pytest.mark.skipif(
    not (ENABLED and os.environ.get("SEARCH_API_KEY") and os.environ.get("LIVE_PROJECT_TITLE")),
    reason="live tests need SHAIDAGO_LIVE_TESTS=1, SEARCH_API_KEY, and LIVE_PROJECT_TITLE",
)
async def test_the_brave_adapter_returns_a_bounded_list_of_public_urls() -> None:
    plan = plan_public_query(
        PublicProjectTerms(title=os.environ["LIVE_PROJECT_TITLE"], locality="Abuja")
    )
    async with httpx.AsyncClient(timeout=10.0) as client:
        provider = BraveSearchProvider(os.environ["SEARCH_API_KEY"], client=client)
        results = await provider.search(plan.query)
    assert results.demo_replay is False
    assert results.provider == "brave"
    assert len(results.urls) <= MAX_RESULTS
    assert all(url.startswith(("http://", "https://")) for url in results.urls)
    print(f"live search ok: {len(results.urls)} URLs, provider {results.provider_version}")  # noqa: T201
