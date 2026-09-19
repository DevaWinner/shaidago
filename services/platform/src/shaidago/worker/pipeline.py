"""Builds the discovery pipeline. The stages arrive with the tasks that own them (BE-091 to
BE-095); until then a run that reaches the worker fails closed with a stable code rather than
pretending to search."""

from shaidago.shared.config import Settings
from shaidago.worker.process import AnalysisResult, DiscoveryPipeline, PermanentStageError
from shaidago.worker.store import RunStore, RunView


class UnconfiguredPipeline:
    async def search(self, run: RunView, store: RunStore) -> None:
        del run, store
        raise PermanentStageError("pipeline_not_configured")

    async def analyse(self, run: RunView, store: RunStore) -> AnalysisResult:
        del run, store
        raise PermanentStageError("pipeline_not_configured")


def build_pipeline(settings: Settings, store: RunStore) -> DiscoveryPipeline:
    del settings, store
    return UnconfiguredPipeline()
