"""The local embedding adapter, exercised with an injected fake model (no download, no ONNX)."""

import asyncio
import importlib
import math
import threading
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest

from shaidago.retrieval.embeddings import EmbeddingUnavailableError
from shaidago.retrieval.local_embeddings import (
    EMBEDDING_DIMENSIONS,
    MAX_IN_FLIGHT,
    MODEL_ID,
    PASSAGE_PREFIX,
    QUERY_PREFIX,
    FastEmbedModel,
    ModelLoader,
    load_fastembed,
    unit_vector,
)

PATH = Path("/not/a/real/model")


class FakeModel:
    """Stands in for fastembed's TextEmbedding: returns a non-unit vector per input."""

    def __init__(self) -> None:
        self.seen: list[list[str]] = []

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        self.seen.append(list(texts))
        # Not unit length on purpose: the real model's raw output has a norm of about 28.
        return [[3.0, 4.0] + [0.0] * (EMBEDDING_DIMENSIONS - 2) for _ in texts]


def loader_for(model: Any) -> ModelLoader:
    def load(path: Path, threads: int) -> Any:
        del path, threads
        return model

    return load


async def opened(model: Any) -> FastEmbedModel:
    embedder = FastEmbedModel(PATH, loader=loader_for(model))
    await embedder.open()
    return embedder


async def test_a_query_is_prefixed_normalised_and_full_width() -> None:
    fake = FakeModel()
    embedder = await opened(fake)
    vector = await embedder.embed_query("How much did it cost?")
    await embedder.close()

    assert fake.seen == [[QUERY_PREFIX + "How much did it cost?"]]
    assert len(vector) == EMBEDDING_DIMENSIONS
    assert math.isclose(sum(v * v for v in vector), 1.0, rel_tol=1e-9)
    assert vector[:2] == pytest.approx((0.6, 0.8))  # 3-4-5, so normalisation is exact


async def test_passages_use_the_passage_prefix_and_keep_their_order() -> None:
    fake = FakeModel()
    embedder = await opened(fake)
    vectors = await embedder.embed(["first chunk", "second chunk"])
    await embedder.close()

    assert fake.seen == [[PASSAGE_PREFIX + "first chunk", PASSAGE_PREFIX + "second chunk"]]
    assert len(vectors) == 2


async def test_a_large_batch_is_split_and_nothing_is_lost() -> None:
    fake = FakeModel()
    embedder = await opened(fake)
    vectors = await embedder.embed([f"chunk {i}" for i in range(70)])
    await embedder.close()

    assert len(vectors) == 70
    assert [len(batch) for batch in fake.seen] == [32, 32, 6]


async def test_an_empty_batch_costs_nothing() -> None:
    fake = FakeModel()
    embedder = await opened(fake)
    assert await embedder.embed([]) == []
    assert fake.seen == []
    await embedder.close()


@pytest.mark.parametrize("text", ["", "   ", "\n\t"])
async def test_blank_text_is_refused_before_it_reaches_the_model(text: str) -> None:
    fake = FakeModel()
    embedder = await opened(fake)
    with pytest.raises(EmbeddingUnavailableError) as raised:
        await embedder.embed_query(text)
    assert raised.value.code == "embedding_empty_text"
    assert fake.seen == []
    await embedder.close()


async def test_long_text_is_truncated_not_rejected() -> None:
    fake = FakeModel()
    embedder = await opened(fake)
    await embedder.embed_query("x" * 100_000)
    await embedder.close()
    assert len(fake.seen[0][0]) == len(QUERY_PREFIX) + 4_000


async def test_a_model_that_fails_to_load_degrades_instead_of_raising() -> None:
    def broken(_path: Path, _threads: int) -> Any:
        raise RuntimeError("/secret/path/leaks/here")

    embedder = FastEmbedModel(PATH, loader=broken)
    await embedder.open()  # must not raise: the API has to start without the model

    assert embedder.available is False
    with pytest.raises(EmbeddingUnavailableError) as raised:
        await embedder.ping()
    assert raised.value.code == "embedding_not_loaded"
    with pytest.raises(EmbeddingUnavailableError):
        await embedder.embed_query("anything")
    await embedder.close()


async def test_a_load_failure_logs_the_class_but_never_the_message(
    capsys: pytest.CaptureFixture[str],
) -> None:
    def broken(_path: Path, _threads: int) -> Any:
        raise RuntimeError("/secret/path/leaks/here")

    embedder = FastEmbedModel(PATH, loader=broken)
    await embedder.open()
    await embedder.close()
    captured = capsys.readouterr()
    assert "/secret/path" not in captured.out + captured.err


async def test_a_call_before_open_and_after_close_is_refused() -> None:
    embedder = FastEmbedModel(PATH, loader=loader_for(FakeModel()))
    with pytest.raises(EmbeddingUnavailableError):
        await embedder.embed_query("too early")
    await embedder.open()
    await embedder.close()
    with pytest.raises(EmbeddingUnavailableError):
        await embedder.embed_query("too late")


@pytest.mark.parametrize(
    ("vector", "code"),
    [
        ([0.0] * (EMBEDDING_DIMENSIONS - 1), "embedding_wrong_size"),
        ([0.0] * (EMBEDDING_DIMENSIONS + 1), "embedding_wrong_size"),
        ([float("nan")] + [0.0] * (EMBEDDING_DIMENSIONS - 1), "embedding_invalid_value"),
        ([float("inf")] + [0.0] * (EMBEDDING_DIMENSIONS - 1), "embedding_invalid_value"),
        ([1e9] + [0.0] * (EMBEDDING_DIMENSIONS - 1), "embedding_invalid_value"),
        ([0.0] * EMBEDDING_DIMENSIONS, "embedding_zero_vector"),
    ],
)
def test_an_unusable_vector_is_never_returned(vector: list[float], code: str) -> None:
    with pytest.raises(EmbeddingUnavailableError) as raised:
        unit_vector(vector)
    assert raised.value.code == code


async def test_a_model_returning_the_wrong_width_is_refused_not_passed_on() -> None:
    class Narrow:
        def embed(self, texts: Sequence[str]) -> list[list[float]]:
            return [[1.0, 2.0] for _ in texts]

    embedder = await opened(Narrow())
    with pytest.raises(EmbeddingUnavailableError) as raised:
        await embedder.embed_query("question")
    assert raised.value.code == "embedding_wrong_size"
    await embedder.close()


async def test_a_model_returning_the_wrong_count_is_refused() -> None:
    class Short:
        def embed(self, texts: Sequence[str]) -> list[list[float]]:
            del texts
            return []

    embedder = await opened(Short())
    with pytest.raises(EmbeddingUnavailableError) as raised:
        await embedder.embed_query("question")
    assert raised.value.code == "embedding_wrong_count"
    await embedder.close()


async def test_an_unexpected_model_error_is_classified_and_never_echoed() -> None:
    class Explodes:
        def embed(self, texts: Sequence[str]) -> list[list[float]]:
            raise ValueError("PRIVATE QUESTION TEXT: " + texts[0])

    embedder = await opened(Explodes())
    with pytest.raises(EmbeddingUnavailableError) as raised:
        await embedder.embed_query("a private question")
    assert raised.value.code == "embedding_failed"
    assert "PRIVATE" not in str(raised.value)
    assert raised.value.__cause__ is None, "the original message must not be chained"
    await embedder.close()


async def test_a_slow_model_times_out_and_still_counts_against_the_cap() -> None:
    release = threading.Event()

    class Slow:
        def embed(self, texts: Sequence[str]) -> list[list[float]]:
            release.wait(timeout=5)
            return [[1.0] + [0.0] * (EMBEDDING_DIMENSIONS - 1) for _ in texts]

    embedder = FastEmbedModel(PATH, loader=loader_for(Slow()), timeout_seconds=0.05)
    await embedder.open()
    try:
        with pytest.raises(EmbeddingUnavailableError) as raised:
            await embedder.embed_query("slow")
        assert raised.value.code == "embedding_timeout"
        # The thread is still running, so the call still occupies a slot until it finishes.
        assert embedder._in_flight == 1  # pyright: ignore[reportPrivateUsage]
    finally:
        release.set()
        await asyncio.sleep(0.1)
        assert embedder._in_flight == 0  # pyright: ignore[reportPrivateUsage]
        await embedder.close()


async def test_a_burst_beyond_the_cap_is_refused_as_busy_instead_of_queued() -> None:
    release = threading.Event()

    class Blocking:
        def embed(self, texts: Sequence[str]) -> list[list[float]]:
            release.wait(timeout=5)
            return [[1.0] + [0.0] * (EMBEDDING_DIMENSIONS - 1) for _ in texts]

    embedder = FastEmbedModel(PATH, loader=loader_for(Blocking()), timeout_seconds=30)
    await embedder.open()
    tasks = [asyncio.create_task(embedder.embed_query(f"q{i}")) for i in range(MAX_IN_FLIGHT)]
    await asyncio.sleep(0.05)
    try:
        with pytest.raises(EmbeddingUnavailableError) as raised:
            await embedder.embed_query("one too many")
        assert raised.value.code == "embedding_busy"
    finally:
        release.set()
        await asyncio.gather(*tasks)
        await embedder.close()


def test_the_model_identity_and_width_are_the_agreed_ones() -> None:
    assert MODEL_ID == "intfloat/multilingual-e5-large"
    assert EMBEDDING_DIMENSIONS == 1024
    assert FastEmbedModel(PATH, loader=loader_for(FakeModel())).model_id == MODEL_ID


@pytest.mark.parametrize("timeout", [0, -1, 61])
def test_the_timeout_is_bounded(timeout: float) -> None:
    with pytest.raises(ValueError, match="timeout"):
        FastEmbedModel(PATH, timeout_seconds=timeout)


def test_at_least_one_thread_is_required() -> None:
    with pytest.raises(ValueError, match="thread"):
        FastEmbedModel(PATH, threads=0)


def test_the_real_loader_is_offline_only_and_switches_telemetry_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The production loader must never download and must disable ONNX Runtime telemetry."""
    import fastembed  # noqa: PLC0415

    runtime: Any = importlib.import_module("onnxruntime")
    calls: list[str] = []
    captured: dict[str, Any] = {}

    class StubTextEmbedding:
        def __init__(self, model: str, **kwargs: Any) -> None:
            calls.append("model")
            captured["model"] = model
            captured.update(kwargs)

    monkeypatch.setattr(runtime, "disable_telemetry_events", lambda: calls.append("telemetry"))
    monkeypatch.setattr(fastembed, "TextEmbedding", StubTextEmbedding)

    load_fastembed(Path("/models/e5"), 3)

    assert calls == ["telemetry", "model"], "telemetry is disabled before the model is created"
    assert captured["model"] == MODEL_ID
    assert captured["local_files_only"] is True, "a load must never reach the network"
    assert captured["specific_model_path"] == "/models/e5"
    assert captured["threads"] == 3
