"""Local text embeddings with FastEmbed and multilingual-e5-large (ADR-0010).

Nothing here leaves the machine: the question and the passages are embedded in-process by an ONNX
model that is read from disk, so no provider key, no egress, and no third party sees a question.

Embedding is an *optional* capability. If the model cannot be loaded the adapter stays closed, every
call raises :class:`EmbeddingUnavailableError`, readiness reports the feature degraded, and the
question service falls back to keyword retrieval and says so in ``retrieval_mode``. It never stops
the API, and it never returns a partial or wrong-sized vector.

Inference is blocking CPU work, so it runs on a small dedicated thread pool, never on the event
loop. Queued work is capped: a burst is refused with a retryable "busy" error instead of building
an unbounded backlog behind a slow request.
"""

import asyncio
import importlib
import math
import threading
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Final

import structlog

from shaidago.retrieval.embeddings import EmbeddingUnavailableError
from shaidago.retrieval.search import EMBEDDING_DIMENSIONS

MODEL_ID: Final = "intfloat/multilingual-e5-large"
# e5 models are trained with these prefixes; without them retrieval quality drops noticeably.
QUERY_PREFIX: Final = "query: "
PASSAGE_PREFIX: Final = "passage: "

WORKER_THREADS: Final = 2
MAX_IN_FLIGHT: Final = 8
DEFAULT_TIMEOUT_SECONDS: Final = 10.0
MAX_TIMEOUT_SECONDS: Final = 60.0
MAX_TEXT_CHARS: Final = 4_000
MAX_BATCH: Final = 32
VALUE_LIMIT: Final = 1e6

_logger = structlog.get_logger("shaidago.embeddings")

ModelLoader = Callable[[Path, int], Any]
"""Builds the underlying model from a directory and a thread count; injected for tests."""


def load_fastembed(model_path: Path, threads: int) -> Any:
    """Load the pinned model from a plain directory, refusing any network access."""
    from fastembed import TextEmbedding  # noqa: PLC0415 - heavy import, only when actually loading

    # ONNX Runtime ships a telemetry hook (it logs "Failed to persist telemetry device ID" at load).
    # Nothing here needs it, and AGENTS.md forbids undocumented telemetry, so it is switched off.
    # Imported dynamically into an Any because the package ships no type stubs.
    runtime: Any = importlib.import_module("onnxruntime")
    runtime.disable_telemetry_events()
    return TextEmbedding(
        MODEL_ID, specific_model_path=str(model_path), local_files_only=True, threads=threads
    )


def unit_vector(values: Sequence[float]) -> tuple[float, ...]:
    """L2-normalise. The raw model output is not unit length (norm about 28)."""
    if len(values) != EMBEDDING_DIMENSIONS:
        raise EmbeddingUnavailableError("embedding_wrong_size")
    if not all(math.isfinite(v) and abs(v) <= VALUE_LIMIT for v in values):
        raise EmbeddingUnavailableError("embedding_invalid_value")
    norm = math.sqrt(sum(v * v for v in values))
    if norm == 0.0:
        raise EmbeddingUnavailableError("embedding_zero_vector")
    return tuple(v / norm for v in values)


class FastEmbedModel:
    """Implements ``EmbeddingModel`` (passages) and the query side of hybrid retrieval."""

    model_id: str = MODEL_ID

    def __init__(
        self,
        model_path: Path,
        *,
        threads: int = WORKER_THREADS,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        loader: ModelLoader = load_fastembed,
    ) -> None:
        if not 0 < timeout_seconds <= MAX_TIMEOUT_SECONDS:
            raise ValueError("embedding timeout must be between 0 and 60 seconds")
        if threads < 1:
            raise ValueError("embedding threads must be at least 1")
        self._path = model_path
        self._threads = threads
        self._timeout = timeout_seconds
        self._loader = loader
        self._model: Any = None
        self._executor: ThreadPoolExecutor | None = None
        self._in_flight = 0
        self._lock = threading.Lock()

    @property
    def available(self) -> bool:
        return self._model is not None

    async def open(self) -> None:
        """Load the model. Failure is recorded, not raised: keyword retrieval still works."""
        self._executor = ThreadPoolExecutor(WORKER_THREADS, thread_name_prefix="embed")
        try:
            self._model = await asyncio.get_running_loop().run_in_executor(
                self._executor, self._loader, self._path, self._threads
            )
        except Exception as error:  # any load failure must degrade, never crash
            # Only the exception class is logged: a path or model message could hold a local path.
            _logger.warning("embedding model unavailable", error_class=type(error).__name__)
            self._model = None

    async def close(self) -> None:
        self._model = None
        executor, self._executor = self._executor, None
        if executor is not None:
            executor.shutdown(wait=False, cancel_futures=True)

    async def ping(self) -> None:
        """Readiness probe for an optional dependency: fails, and only degrades, if not loaded."""
        if self._model is None:
            raise EmbeddingUnavailableError("embedding_not_loaded")

    async def embed_query(self, text: str) -> tuple[float, ...]:
        (vector,) = await self._embed([QUERY_PREFIX + self._bounded(text)])
        return vector

    async def embed(self, texts: Sequence[str]) -> Sequence[Sequence[float]]:
        """Passage vectors for the explicit generation command."""
        if not texts:
            return []
        vectors: list[tuple[float, ...]] = []
        for offset in range(0, len(texts), MAX_BATCH):
            batch = [PASSAGE_PREFIX + self._bounded(t) for t in texts[offset : offset + MAX_BATCH]]
            vectors.extend(await self._embed(batch))
        return vectors

    @staticmethod
    def _bounded(text: str) -> str:
        if not text.strip():
            raise EmbeddingUnavailableError("embedding_empty_text")
        return text[:MAX_TEXT_CHARS]

    async def _embed(self, prefixed: list[str]) -> list[tuple[float, ...]]:
        model, executor = self._model, self._executor
        if model is None or executor is None:
            raise EmbeddingUnavailableError("embedding_not_loaded")
        with self._lock:
            if self._in_flight >= MAX_IN_FLIGHT:
                raise EmbeddingUnavailableError("embedding_busy")
            self._in_flight += 1

        def run() -> list[tuple[float, ...]]:
            try:
                return [unit_vector(list(map(float, v))) for v in model.embed(prefixed)]
            finally:
                # Released here, not by the awaiting side: a timed-out call still occupies its
                # thread until it finishes, and must keep counting against the cap until then.
                with self._lock:
                    self._in_flight -= 1

        try:
            future = asyncio.get_running_loop().run_in_executor(executor, run)
        except RuntimeError:  # the pool was shut down between the check above and now
            with self._lock:
                self._in_flight -= 1
            raise EmbeddingUnavailableError("embedding_not_loaded") from None
        try:
            result = await asyncio.wait_for(future, self._timeout)
        except TimeoutError:
            raise EmbeddingUnavailableError("embedding_timeout") from None
        except EmbeddingUnavailableError:
            raise
        except Exception as error:  # the model may raise anything; classify it safely
            _logger.warning("embedding failed", error_class=type(error).__name__)
            raise EmbeddingUnavailableError("embedding_failed") from None
        if len(result) != len(prefixed):
            raise EmbeddingUnavailableError("embedding_wrong_count")
        return result
