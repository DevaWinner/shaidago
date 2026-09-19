"""Where fetched pages come from: the real safe fetcher, or recorded pages in replay mode."""

import json
from pathlib import Path
from typing import Final, Protocol

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from shaidago.discovery.dedupe import canonical_url
from shaidago.discovery.fetcher import FetchedPage, FetchError
from shaidago.discovery.netguard import UnsafeDestinationError, is_public_address, parse_target

FIXTURE_ROOT: Final = Path(__file__).parents[5] / "data" / "discovery-fixtures"
MAX_FIXTURE_BODY: Final = 500_000


class PageFetcher(Protocol):
    async def fetch(self, url: str) -> FetchedPage: ...


class _PageRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    url: str = Field(min_length=8, max_length=2048)
    content_type: str = Field(pattern=r"^[a-z]+/[a-z0-9.+-]+$")
    body: str = Field(max_length=MAX_FIXTURE_BODY)
    error: str | None = Field(default=None, pattern=r"^[a-z_]{3,40}$")


class _PageFile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    fixture_version: int = Field(ge=1, le=1)
    pages: tuple[_PageRecord, ...] = Field(max_length=100)


class FixturePageFetcher:
    """Serves recorded or synthetic pages by canonical URL; never touches the network."""

    def __init__(self, pages: dict[str, _PageRecord]) -> None:
        self._pages = pages

    @classmethod
    def from_file(cls, path: Path) -> FixturePageFetcher:
        try:
            parsed = _PageFile.model_validate(json.loads(path.read_text("utf-8")))
        except OSError, ValueError, ValidationError:
            raise FetchError("bad_fixture") from None
        return cls({canonical_url(p.url): p for p in parsed.pages})

    @classmethod
    def empty(cls) -> FixturePageFetcher:
        return cls({})

    async def fetch(self, url: str) -> FetchedPage:
        # Replay honours the same destination rules as the live fetcher, so an unsafe URL in a
        # recorded result is refused, not served.
        target = parse_target(url)
        if target.is_ip_literal and not is_public_address(target.host):
            raise UnsafeDestinationError("private_address")
        record = self._pages.get(canonical_url(url))
        if record is None:
            raise FetchError("fixture_missing")
        if record.error is not None:
            raise FetchError(record.error)
        return FetchedPage(record.url, 200, record.content_type, record.body.encode())
