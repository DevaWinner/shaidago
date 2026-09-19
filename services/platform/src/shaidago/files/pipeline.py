"""Streaming intake: bound, sniff, scan, sanitise, then store only the sanitised artifact.

The raw upload lives only in a private temporary file that is deleted on every path, including
rejection, timeout, and crash of the request. Nothing about the content is logged or returned
beyond a stable rejection reason.
"""

import asyncio
import hashlib
import os
import tempfile
from collections.abc import AsyncIterable, Callable
from concurrent.futures import Executor
from dataclasses import dataclass
from functools import partial
from pathlib import Path

from shaidago.files.rules import (
    FileLimits,
    UploadRejectedError,
    safe_display_name,
    sniff,
)
from shaidago.files.sanitise import sanitise
from shaidago.files.scanner import MalwareScanner
from shaidago.files.storage import ObjectStore, new_object_key


@dataclass(frozen=True)
class StoredEvidence:
    """What the database row for an evidence file needs; every state is a vocabulary value."""

    object_key: str
    mime_type: str
    size_bytes: int
    sha256: str
    display_name: str
    sanitation_state: str
    scan_state: str


@dataclass(frozen=True)
class PipelineParts:
    """The external collaborators, injected so tests can substitute deterministic doubles."""

    scanner: MalwareScanner
    store: ObjectStore
    executor: Executor


class EvidencePipeline:
    def __init__(
        self,
        parts: PipelineParts,
        *,
        limits: FileLimits | None = None,
        scratch_dir: Path | None = None,
        key_factory: Callable[[], str] = new_object_key,
    ) -> None:
        self._scanner = parts.scanner
        self._store = parts.store
        self._executor = parts.executor
        self._limits = limits or FileLimits()
        self._scratch = scratch_dir
        self._new_key = key_factory

    async def process(
        self,
        chunks: AsyncIterable[bytes],
        *,
        filename: str,
        declared_mime: str | None = None,
    ) -> StoredEvidence:
        limits = self._limits
        path = await self._spool(chunks)
        try:
            data = await asyncio.to_thread(path.read_bytes)
        finally:
            await asyncio.to_thread(path.unlink, missing_ok=True)
        mime = sniff(data[:16])
        if mime is None:
            raise UploadRejectedError("unsupported_type")
        if declared_mime is not None and declared_mime != mime:
            raise UploadRejectedError("spoofed_type")
        # Scan the raw bytes before any parser touches them, then the artifact we will keep.
        await self._scanner.scan(data)
        clean = await self._sanitise(data, mime)
        del data
        scan_state = await self._scanner.scan(clean)
        key = self._new_key()
        try:
            await asyncio.wait_for(
                self._store.put(key, clean, mime), timeout=limits.store_timeout_seconds
            )
        except TimeoutError:
            raise UploadRejectedError("storage_failed") from None
        return StoredEvidence(
            object_key=key,
            mime_type=mime,
            size_bytes=len(clean),
            sha256=hashlib.sha256(clean).hexdigest(),
            display_name=safe_display_name(filename, mime),
            sanitation_state="sanitised",
            scan_state=scan_state,
        )

    async def _spool(self, chunks: AsyncIterable[bytes]) -> Path:
        """Write the stream to a private temp file, refusing as soon as the cap is crossed."""
        handle, name = await asyncio.to_thread(
            partial(tempfile.mkstemp, prefix="sg-upload-", dir=self._scratch)
        )
        path = Path(name)
        total = 0
        try:
            with os.fdopen(handle, "wb") as out:
                async for chunk in chunks:
                    total += len(chunk)
                    if total > self._limits.max_file_bytes:
                        raise UploadRejectedError("too_large")
                    await asyncio.to_thread(out.write, chunk)
        except BaseException:
            await asyncio.to_thread(path.unlink, missing_ok=True)
            raise
        return path

    async def _sanitise(self, data: bytes, mime: str) -> bytes:
        loop = asyncio.get_running_loop()
        job = loop.run_in_executor(self._executor, sanitise, data, mime, self._limits)
        try:
            return await asyncio.wait_for(job, timeout=self._limits.sanitise_timeout_seconds)
        except TimeoutError:
            raise UploadRejectedError("timeout") from None


def sweep_stale_uploads(scratch_dir: Path | None = None) -> int:
    """Startup cleanup for temp files a crashed process left behind."""
    root = scratch_dir or Path(tempfile.gettempdir())
    removed = 0
    for leftover in root.glob("sg-upload-*"):
        leftover.unlink(missing_ok=True)
        removed += 1
    return removed
