"""Chooses live or replay providers for discovery from validated settings (ADR-0008)."""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Final

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from shaidago.discovery.analysis import AnalysisProvider, FixtureAnalyser, LiveAnalyser
from shaidago.discovery.fetcher import SafeFetcher
from shaidago.discovery.netguard import SystemResolver
from shaidago.discovery.pages import FIXTURE_ROOT, FixturePageFetcher, PageFetcher
from shaidago.discovery.search import BraveSearchProvider, FixtureSearchProvider, SearchProvider
from shaidago.retrieval.groq import GroqLanguageModel
from shaidago.shared.config import Settings


class _AnalysisRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    output: dict[str, object]


class _AnalysisFile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    fixture_version: int = Field(ge=1, le=1)
    records: tuple[_AnalysisRecord, ...] = Field(max_length=100)


ANALYSIS_FIXTURE: Final = "analysis.json"


def load_analysis_fixtures(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    try:
        parsed = _AnalysisFile.model_validate(json.loads(path.read_text("utf-8")))
    except OSError, ValueError, ValidationError:
        raise ValueError("discovery analysis fixture is invalid") from None
    return {r.fingerprint: json.dumps(r.output) for r in parsed.records}


class Providers:
    def __init__(
        self,
        search: SearchProvider,
        fetcher: PageFetcher,
        analyser_for: Callable[[str], AnalysisProvider],
    ) -> None:
        self.search = search
        self.fetcher = fetcher
        self.analyser_for = analyser_for


def replay_providers(root: Path = FIXTURE_ROOT) -> Providers:
    search = root / "search.json"
    pages = root / "pages.json"
    analyser = FixtureAnalyser(load_analysis_fixtures(root / ANALYSIS_FIXTURE))
    return Providers(
        FixtureSearchProvider.from_file(search) if search.exists() else FixtureSearchProvider({}),
        FixturePageFetcher.from_file(pages) if pages.exists() else FixturePageFetcher.empty(),
        lambda _scope: analyser,
    )


def build_providers(settings: Settings) -> Providers:
    config = settings.providers
    if config.mode == "replay":
        return replay_providers()
    if config.search_api_key is None or config.language_api_key is None:
        raise ValueError("live discovery needs SEARCH_API_KEY and GROQ_API_KEY")
    transport = GroqLanguageModel(
        api_key=config.language_api_key.get_secret_value(),
        base_url=config.language_base_url,
        model_id=config.qa_model,
    )
    # Public runs use the smaller model; only reviewer (report-scoped) runs use synthesis.
    public = LiveAnalyser(transport, config.qa_model)
    private = LiveAnalyser(transport, config.discovery_model)
    return Providers(
        BraveSearchProvider(
            config.search_api_key.get_secret_value(), client=httpx.AsyncClient(timeout=10.0)
        ),
        SafeFetcher(SystemResolver()),
        lambda scope: private if scope == "report" else public,
    )
