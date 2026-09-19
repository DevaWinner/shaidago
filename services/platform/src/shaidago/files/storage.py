"""Private object storage for sanitised evidence. Keys are random and describe nothing."""

import asyncio
import secrets
from typing import Any, Final, Protocol

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from shaidago.files.rules import UploadRejectedError

_KEY_BYTES: Final = 16


def new_object_key() -> str:
    """128 random bits as hex: no person, project, or report name can appear in a key."""
    return secrets.token_hex(_KEY_BYTES)


class ObjectStore(Protocol):
    async def put(self, key: str, data: bytes, content_type: str) -> None: ...
    async def get(self, key: str) -> bytes: ...
    async def delete(self, key: str) -> None: ...


class InMemoryObjectStore:
    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        self.objects[key] = (data, content_type)

    async def get(self, key: str) -> bytes:
        return self.objects[key][0]

    async def delete(self, key: str) -> None:
        self.objects.pop(key, None)


class S3ObjectStore:
    """S3 API (MinIO locally, R2 hosted). boto3 is blocking, so calls run in a worker thread."""

    def __init__(
        self,
        *,
        endpoint_url: str,
        bucket: str,
        access_key_id: str,
        secret_access_key: str,
        timeout_seconds: float,
    ) -> None:
        self._bucket = bucket
        # Stub overloads for uninstalled services resolve to Unknown, so the client is Any-typed.
        self._client: Any = boto3.client(  # pyright: ignore[reportUnknownMemberType]
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name="auto",
            config=Config(
                connect_timeout=timeout_seconds,
                read_timeout=timeout_seconds,
                retries={"max_attempts": 2},
                s3={"addressing_style": "path"},
            ),
        )

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        await self._call(
            self._client.put_object,
            Bucket=self._bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
            ContentDisposition="attachment",
        )

    async def get(self, key: str) -> bytes:
        response = await self._call(self._client.get_object, Bucket=self._bucket, Key=key)
        return bytes(await asyncio.to_thread(response["Body"].read))

    async def delete(self, key: str) -> None:
        await self._call(self._client.delete_object, Bucket=self._bucket, Key=key)

    async def check(self) -> None:
        """Readiness: the configured bucket exists and these credentials can reach it."""
        await self._call(self._client.head_bucket, Bucket=self._bucket)

    @staticmethod
    async def _call(function: Any, **arguments: Any) -> Any:
        try:
            return await asyncio.to_thread(function, **arguments)
        except BotoCoreError, ClientError:
            raise UploadRejectedError("storage_failed") from None
