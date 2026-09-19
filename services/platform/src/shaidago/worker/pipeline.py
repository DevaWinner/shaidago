"""Builds the discovery pipeline for the worker process."""

from shaidago.discovery.pipeline import SourceScoutPipeline
from shaidago.discovery.providers import build_providers
from shaidago.shared.config import Settings
from shaidago.worker.process import DiscoveryPipeline
from shaidago.worker.store import RunStore


def build_pipeline(settings: Settings, store: RunStore) -> DiscoveryPipeline:
    del store  # stages receive the store per call
    providers = build_providers(settings)
    return SourceScoutPipeline(providers.search, providers.fetcher, providers.analyser_for)
