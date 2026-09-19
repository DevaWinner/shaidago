"""The search provider boundary: URLs only, capped, bounded, and never trusted as evidence.

A provider returns candidate URLs and nothing else. Ranks, snippets, and popularity are not part
of the result type, so they cannot be persisted or treated as truth by accident. Every query is
re-screened by the planner's outbound check before any request is made. Failures are classified
(retryable, non-retryable) and never carry the query, the response, or the credential.
"""

import asyncio
import hashlib
import json
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, Protocol
from urllib.parse import urlsplit

import httpx
import structlog
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from shaidago.discovery.planner import UnsafeQueryError, assert_query_safe

MAX_RESULTS: Final = 10
HTTP_OK: Final = 200
HTTP_TOO_MANY_REQUESTS: Final = 429
HTTP_SERVER_ERROR: Final = 500
MAX_RESPONSE_BYTES: Final = 1_000_000
MAX_URL_CHARS: Final = 2048
BRAVE_ENDPOINT: Final = "https://api.search.brave.com/res/v1/web/search"
BRAVE_VERSION: Final = "brave-web-v1"
FIXTURE_ROOT: Final = Path(__file__).parents[5] / "data" / "discovery-fixtures"
_logger = structlog.get_logger("shaidago.discovery.search")


class SearchUnavailableError(Exception):
    """Retryable: the provider was slow, rate limiting, or failing. Carries no request content."""


class SearchRejectedError(Exception):
    """Not retryable: the provider refused the request or returned something unusable."""


@dataclass(frozen=True)
class SearchResults:
    urls: tuple[str, ...]
    provider: str
    provider_version: str
    demo_replay: bool


class SearchProvider(Protocol):
    async def search(self, query: str) -> SearchResults: ...


def _clean_urls(candidates: list[object]) -> tuple[str, ...]:
    seen: set[str] = set()
    urls: list[str] = []
    for candidate in candidates:
        if not isinstance(candidate, str) or len(candidate) > MAX_URL_CHARS:
            continue
        parts = urlsplit(candidate)
        if parts.scheme not in {"http", "https"} or not parts.hostname:
            continue
        if candidate not in seen:
            seen.add(candidate)
            urls.append(candidate)
        if len(urls) == MAX_RESULTS:
            break
    return tuple(urls)


class BraveSearchProvider:
    """Brave Search API. At most ten URLs, a strict timeout, and bounded retries."""

    def __init__(
        self,
        api_key: str,
        *,
        client: httpx.AsyncClient,
        max_attempts: int = 2,
        backoff_seconds: float = 0.5,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._api_key = api_key
        self._client = client
        self._max_attempts = max_attempts
        self._backoff = backoff_seconds
        self._sleep = sleep

    def __repr__(self) -> str:
        return "BraveSearchProvider(<redacted>)"

    async def search(self, query: str) -> SearchResults:
        assert_query_safe(query)  # raises UnsafeQueryError before any request exists
        started = time.monotonic()
        for attempt in range(1, self._max_attempts + 1):
            try:
                return await self._once(query, attempt, started)
            except SearchUnavailableError:
                if attempt == self._max_attempts:
                    _logger.warning("search unavailable", attempts=attempt, provider="brave")
                    raise
                await self._sleep(self._backoff * 2 ** (attempt - 1))
        raise SearchUnavailableError  # pragma: no cover - the loop always returns or raises

    async def _once(self, query: str, attempt: int, started: float) -> SearchResults:
        try:
            response = await self._client.get(
                BRAVE_ENDPOINT,
                params={"q": query, "count": MAX_RESULTS, "safesearch": "moderate"},
                headers={"X-Subscription-Token": self._api_key, "Accept": "application/json"},
            )
        except httpx.HTTPError:
            raise SearchUnavailableError from None
        status = response.status_code
        if status == HTTP_TOO_MANY_REQUESTS or status >= HTTP_SERVER_ERROR:
            raise SearchUnavailableError
        if status != HTTP_OK or len(response.content) > MAX_RESPONSE_BYTES:
            raise SearchRejectedError
        try:
            payload: Any = response.json()
            hits: list[object] = list(payload["web"]["results"])
        except ValueError, KeyError, TypeError:
            raise SearchRejectedError from None
        urls = _clean_urls([hit.get("url") for hit in hits if isinstance(hit, dict)])  # type: ignore[reportUnknownMemberType]
        _logger.info(
            "search completed",
            provider="brave",
            result_count=len(urls),
            attempts=attempt,
            latency_ms=int((time.monotonic() - started) * 1000),
        )
        return SearchResults(urls, "brave", BRAVE_VERSION, demo_replay=False)


class _FixtureEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    query_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    urls: tuple[str, ...] = Field(default=(), max_length=MAX_RESULTS)
    error: str | None = Field(default=None, pattern=r"^(unavailable|rejected)$")


class _FixtureFile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    fixture_version: int = Field(ge=1, le=1)
    entries: tuple[_FixtureEntry, ...] = Field(max_length=200)


def query_fingerprint(query: str) -> str:
    return hashlib.sha256(query.strip().casefold().encode()).hexdigest()


class FixtureSearchProvider:
    """Replays recorded or synthetic results by query fingerprint; never touches the network.

    Every result is labelled ``demo_replay``. A query with no fixture returns no results.
    """

    def __init__(self, entries: dict[str, _FixtureEntry]) -> None:
        self._entries = entries

    @classmethod
    def from_file(cls, path: Path) -> FixtureSearchProvider:
        try:
            parsed = _FixtureFile.model_validate(json.loads(path.read_text("utf-8")))
        except OSError, ValueError, ValidationError:
            raise SearchRejectedError from None
        return cls({entry.query_sha256: entry for entry in parsed.entries})

    async def search(self, query: str) -> SearchResults:
        assert_query_safe(query)
        entry = self._entries.get(query_fingerprint(query))
        if entry is not None and entry.error == "unavailable":
            raise SearchUnavailableError
        if entry is not None and entry.error == "rejected":
            raise SearchRejectedError
        urls = _clean_urls(list(entry.urls)) if entry is not None else ()
        return SearchResults(urls, "fixture", "fixture-v1", demo_replay=True)


__all__ = [
    "BRAVE_ENDPOINT",
    "MAX_RESULTS",
    "BraveSearchProvider",
    "FixtureSearchProvider",
    "SearchProvider",
    "SearchRejectedError",
    "SearchResults",
    "SearchUnavailableError",
    "UnsafeQueryError",
    "query_fingerprint",
]
