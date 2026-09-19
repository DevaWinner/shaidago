"""Malware scanning behind a small port. Any failure to scan is a rejection, never a pass."""

import asyncio
import struct
from typing import Final, Protocol

from shaidago.files.rules import UploadRejectedError

EICAR: Final = rb"X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
_CHUNK: Final = 64 * 1024


class MalwareScanner(Protocol):
    async def scan(self, data: bytes) -> str:
        """Return a ``malware_scan_state`` of ``clean`` or ``not_scanned_demo``.

        Raises ``UploadRejectedError`` for ``malware_detected`` or ``scan_failed``.
        """
        ...


class ClamdScanner:
    """ClamAV over the clamd INSTREAM protocol on TCP, with one overall time limit."""

    def __init__(self, host: str, port: int, *, timeout_seconds: float) -> None:
        self._host = host
        self._port = port
        self._timeout = timeout_seconds

    async def scan(self, data: bytes) -> str:
        try:
            reply = await asyncio.wait_for(self._exchange(data), self._timeout)
        except TimeoutError, OSError, asyncio.IncompleteReadError:
            raise UploadRejectedError("scan_failed") from None
        if reply.endswith("OK"):
            return "clean"
        if reply.endswith("FOUND"):
            raise UploadRejectedError("malware_detected")
        raise UploadRejectedError("scan_failed")

    async def _exchange(self, data: bytes) -> str:
        reader, writer = await asyncio.open_connection(self._host, self._port)
        try:
            writer.write(b"zINSTREAM\0")
            for start in range(0, len(data), _CHUNK):
                chunk = data[start : start + _CHUNK]
                writer.write(struct.pack(">I", len(chunk)) + chunk)
            writer.write(struct.pack(">I", 0))
            await writer.drain()
            return (await reader.readuntil(b"\0")).rstrip(b"\0").decode("ascii", "replace").strip()
        finally:
            writer.close()
            await writer.wait_closed()


class NotDeployedScanner:
    """Hosted demo only: files are labelled ``not_scanned_demo``. Production refuses this mode."""

    async def scan(self, data: bytes) -> str:
        del data
        return "not_scanned_demo"


class EicarScanner:
    """Deterministic test double that flags the industry-standard EICAR test string."""

    async def scan(self, data: bytes) -> str:
        if EICAR in data:
            raise UploadRejectedError("malware_detected")
        return "clean"


def build_scanner(
    mode: str, *, app_env: str, host: str, port: int, timeout_seconds: float
) -> MalwareScanner:
    if mode == "not_deployed":
        if app_env == "production":
            raise ValueError("SCANNER_MODE=not_deployed is refused in production")
        return NotDeployedScanner()
    return ClamdScanner(host, port, timeout_seconds=timeout_seconds)
