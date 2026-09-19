"""The S3 adapter and the full pipeline against the Compose MinIO (``make infra-up``)."""

import io
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import boto3
import pytest
from botocore.exceptions import ClientError
from PIL import Image

from shaidago.files.pipeline import EvidencePipeline, PipelineParts
from shaidago.files.rules import FileLimits, UploadRejectedError
from shaidago.files.scanner import EicarScanner
from shaidago.files.storage import S3ObjectStore


def _setting(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        pytest.fail(f"{name} is not set. Run `make backend-integration` with infra up.")
    return value


def assert_empty(directory: Path) -> None:
    assert list(directory.iterdir()) == []


@pytest.fixture
def store() -> S3ObjectStore:
    endpoint, bucket = _setting("OBJECT_STORE_ENDPOINT_URL"), _setting("OBJECT_STORE_BUCKET")
    access, secret = (
        _setting("OBJECT_STORE_ACCESS_KEY_ID"),
        _setting("OBJECT_STORE_SECRET_ACCESS_KEY"),
    )
    admin = boto3.client(  # pyright: ignore[reportUnknownMemberType]
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access,
        aws_secret_access_key=secret,
        region_name="auto",
    )
    try:
        admin.head_bucket(Bucket=bucket)
    except ClientError:
        admin.create_bucket(Bucket=bucket)
    return S3ObjectStore(
        endpoint_url=endpoint,
        bucket=bucket,
        access_key_id=access,
        secret_access_key=secret,
        timeout_seconds=5,
    )


async def test_round_trip_through_the_pipeline_stores_only_the_sanitised_artifact(
    store: S3ObjectStore, tmp_path: Path
) -> None:
    image = Image.new("RGB", (40, 40), "green")
    exif = Image.Exif()
    exif[0x010E] = "MINIO-CANARY"
    raw = io.BytesIO()
    image.save(raw, "JPEG", exif=exif)

    async def chunks():
        yield raw.getvalue()

    with ThreadPoolExecutor(max_workers=1) as pool:
        pipeline = EvidencePipeline(
            PipelineParts(EicarScanner(), store, pool),
            limits=FileLimits(max_dimension=64),
            scratch_dir=tmp_path,
        )
        result = await pipeline.process(chunks(), filename="site.jpg", declared_mime="image/jpeg")
    try:
        assert b"MINIO-CANARY" not in await store.get(result.object_key)
        assert_empty(tmp_path)
    finally:
        await store.delete(result.object_key)
    with pytest.raises(UploadRejectedError) as raised:
        await store.get(result.object_key)
    assert raised.value.reason == "storage_failed"


async def test_an_unreachable_store_is_a_clean_failure() -> None:
    dead = S3ObjectStore(
        endpoint_url="http://127.0.0.1:1",
        bucket="none",
        access_key_id="a",
        secret_access_key="b",
        timeout_seconds=0.5,
    )
    with pytest.raises(UploadRejectedError) as raised:
        await dead.put("k", b"x", "image/png")
    assert raised.value.reason == "storage_failed"
