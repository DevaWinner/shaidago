"""Readiness probes and the real ClamAV scanner against the Compose services (``make infra-up``)."""

import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from redis.asyncio import Redis

from shaidago.files.pipeline import EvidencePipeline, PipelineParts
from shaidago.files.rules import FileLimits, UploadRejectedError
from shaidago.files.scanner import EICAR, ClamdScanner
from shaidago.files.storage import InMemoryObjectStore, S3ObjectStore
from shaidago.shared.health import evaluate_readiness
from shaidago.shared.probes import CallableProbe
from shaidago.shared.ratelimit import RedisRateLimiter
from tests.unit.files.test_evidence_pipeline import png


def _env(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if not value:
        pytest.fail(f"{name} is not set. Run `make backend-integration` with infra up.")
    return value


def clamd(port: int | None = None) -> ClamdScanner:
    return ClamdScanner(
        "127.0.0.1", port or int(_env("INFRA_CLAMD_PORT", "53310")), timeout_seconds=20
    )


async def one_chunk(data: bytes):
    yield data


def redis_client(port: int) -> Redis:
    return Redis(
        host="127.0.0.1",
        port=port,
        password=os.environ.get("REDIS_PASSWORD"),
        socket_connect_timeout=1,
        socket_timeout=1,
    )


async def test_the_redis_probe_passes_against_redis_and_fails_when_it_is_gone() -> None:
    good = RedisRateLimiter(redis_client(int(_env("INFRA_REDIS_PORT", "56379"))))
    await good.check()
    dead = RedisRateLimiter(redis_client(1))
    with pytest.raises(Exception, match=r".+"):
        await dead.check()


def storage(bucket: str, endpoint: str | None = None) -> S3ObjectStore:
    return S3ObjectStore(
        endpoint_url=endpoint or _env("OBJECT_STORE_ENDPOINT_URL"),
        bucket=bucket,
        access_key_id=_env("OBJECT_STORE_ACCESS_KEY_ID"),
        secret_access_key=_env("OBJECT_STORE_SECRET_ACCESS_KEY"),
        timeout_seconds=3,
    )


async def test_the_object_storage_probe_needs_a_reachable_existing_bucket() -> None:
    await storage(_env("OBJECT_STORE_BUCKET")).check()
    for broken in (storage("no-such-bucket-here"), storage("x-bucket", "http://127.0.0.1:1")):
        with pytest.raises(UploadRejectedError):
            await broken.check()


async def test_the_scanner_probe_and_a_real_scan_of_clean_and_infected_content() -> None:
    scanner = clamd()
    await scanner.ping()
    assert await scanner.scan(png()) == "clean"
    # ClamAV recognises the standard test file as a whole file; appended to an image it is not
    # matched, which is why the pipeline also refuses anything that is not a clean image or PDF.
    with pytest.raises(UploadRejectedError) as raised:
        await scanner.scan(EICAR)
    assert raised.value.reason == "malware_detected"


async def test_the_pipeline_with_the_real_scanner_stores_a_clean_file(tmp_path: Path) -> None:
    store = InMemoryObjectStore()
    with ThreadPoolExecutor(max_workers=1) as pool:
        pipeline = EvidencePipeline(
            PipelineParts(clamd(), store, pool),
            limits=FileLimits(max_dimension=64),
            scratch_dir=tmp_path,
        )
        stored = await pipeline.process(one_chunk(png()), filename="a.png")
    assert stored.scan_state == "clean"
    assert len(store.objects) == 1
    assert not os.listdir(tmp_path)  # noqa: PTH208 - a one-off check after the work


async def test_a_dead_scanner_fails_the_probe_and_the_scan_closed() -> None:
    dead = clamd(port=1)
    with pytest.raises(RuntimeError):
        await dead.ping()
    with pytest.raises(UploadRejectedError) as raised:
        await dead.scan(b"x")
    assert raised.value.reason == "scan_failed"


async def test_readiness_reports_each_dependency_and_goes_unavailable_when_one_fails() -> None:
    healthy = [
        CallableProbe(
            "redis",
            RedisRateLimiter(redis_client(int(_env("INFRA_REDIS_PORT", "56379")))).check,
            required=True,
        ),
        CallableProbe("object_storage", storage(_env("OBJECT_STORE_BUCKET")).check, required=True),
        CallableProbe("scanner", clamd().ping, required=True),
    ]
    ok = await evaluate_readiness(tuple(healthy), 5)
    assert (ok.status, ok.components) == (
        "ready",
        {"redis": "ok", "object_storage": "ok", "scanner": "ok"},
    )
    broken = [*healthy[:2], CallableProbe("scanner", clamd(port=1).ping, required=True)]
    down = await evaluate_readiness(tuple(broken), 5)
    assert down.status == "unavailable"
    assert down.components["scanner"] == "unavailable"
