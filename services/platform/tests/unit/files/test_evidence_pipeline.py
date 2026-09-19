"""The evidence pipeline against hostile and malformed uploads. All fixtures are synthetic."""

import asyncio
import io
import re
import time
from collections.abc import AsyncIterator, Iterator
from concurrent.futures import Executor, ProcessPoolExecutor, ThreadPoolExecutor
from pathlib import Path

import pikepdf
import pytest
from PIL import Image

from shaidago.files.pipeline import (
    EvidencePipeline,
    PipelineParts,
    StoredEvidence,
    sweep_stale_uploads,
)
from shaidago.files.rules import FileLimits, UploadRejectedError, safe_display_name, sniff
from shaidago.files.scanner import (
    EICAR,
    ClamdScanner,
    EicarScanner,
    NotDeployedScanner,
    build_scanner,
)
from shaidago.files.storage import InMemoryObjectStore, new_object_key
from shaidago.shared import vocabulary

GPS_MARKER = b"GPSLATITUDE-CANARY"
SMALL = FileLimits(max_file_bytes=200_000, max_pixels=1_000_000, max_dimension=64)


async def stream(data: bytes, size: int = 1000) -> AsyncIterator[bytes]:
    for start in range(0, len(data), size):
        yield data[start : start + size]
        await asyncio.sleep(0)


def png(width: int = 32, height: int = 32) -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (width, height), "white").save(out, "PNG")
    return out.getvalue()


def jpeg_with_gps() -> bytes:
    image = Image.new("RGB", (200, 100), "blue")
    exif = Image.Exif()
    exif[0x010E] = GPS_MARKER.decode()  # ImageDescription carries a canary string
    exif[0x8825] = {1: "N", 2: (9.0, 4.0, 0.0), 3: "E", 4: (7.0, 29.0, 0.0)}
    out = io.BytesIO()
    image.save(out, "JPEG", exif=exif)
    return out.getvalue()


def pdf_bytes(*, encrypt: bool = False, hostile: bool = False, pages: int = 1) -> bytes:
    pdf = pikepdf.new()
    for _ in range(pages):
        pdf.add_blank_page()
    pdf.docinfo["/Author"] = "Canary Author"
    if hostile:
        pdf.Root.OpenAction = pikepdf.Dictionary(
            S=pikepdf.Name.JavaScript, JS=pikepdf.String("app.alert(1)")
        )
        pdf.attachments["x.txt"] = b"payload"
    out = io.BytesIO()
    if encrypt:
        pdf.save(out, encryption=pikepdf.Encryption(owner="o", user="u"))
    else:
        pdf.save(out)
    return out.getvalue()


@pytest.fixture
def scratch(tmp_path: Path) -> Path:
    directory = tmp_path / "scratch"
    directory.mkdir()
    return directory


@pytest.fixture
def store() -> InMemoryObjectStore:
    return InMemoryObjectStore()


@pytest.fixture
def executor() -> Iterator[Executor]:
    with ThreadPoolExecutor(max_workers=2) as pool:
        yield pool


def make(
    store: InMemoryObjectStore,
    executor: Executor,
    scratch: Path,
    *,
    scanner: object | None = None,
    limits: FileLimits = SMALL,
) -> EvidencePipeline:
    parts = PipelineParts(scanner or EicarScanner(), store, executor)  # pyright: ignore[reportArgumentType]
    return EvidencePipeline(parts, limits=limits, scratch_dir=scratch)


async def rejected(pipeline: EvidencePipeline, data: bytes, **kw: str) -> str:
    with pytest.raises(UploadRejectedError) as raised:
        await pipeline.process(stream(data), filename="a.bin", **kw)
    return raised.value.reason


def assert_clean_scratch(scratch: Path) -> None:
    assert list(scratch.iterdir()) == [], "no raw upload may remain on disk"


def assert_clean(store: InMemoryObjectStore, scratch: Path) -> None:
    assert_clean_scratch(scratch)
    assert store.objects == {}, "a rejected file stores nothing"


async def test_gps_metadata_is_removed_and_only_the_clean_copy_is_stored(
    store: InMemoryObjectStore, executor: Executor, scratch: Path
) -> None:
    raw = jpeg_with_gps()
    assert GPS_MARKER in raw
    result = await make(store, executor, scratch).process(
        stream(raw), filename="../../Photo of site!.JPEG", declared_mime="image/jpeg"
    )
    stored, content_type = store.objects[result.object_key]
    assert content_type == "image/jpeg"
    assert GPS_MARKER not in stored
    assert not Image.open(io.BytesIO(stored)).getexif()
    assert len(result.sha256) == 64
    assert result.size_bytes == len(stored)
    assert (result.sanitation_state, result.scan_state) == ("sanitised", "clean")
    assert result.display_name == "Photo of site.jpg"
    assert re.fullmatch(r"[0-9a-f]{32}", result.object_key)
    assert_clean_scratch(scratch)


async def test_large_images_are_scaled_down_and_png_round_trips(
    store: InMemoryObjectStore, executor: Executor, scratch: Path
) -> None:
    result = await make(store, executor, scratch).process(stream(png(300, 150)), filename="a.png")
    assert max(Image.open(io.BytesIO(store.objects[result.object_key][0])).size) == 64


@pytest.mark.parametrize(
    ("data", "reason"),
    [
        (
            b"<svg xmlns='http://www.w3.org/2000/svg'><script>alert(1)</script></svg>",
            "unsupported_type",
        ),
        (b"<html><script>alert(1)</script></html>", "unsupported_type"),
        (b"MZ\x90\x00 executable", "unsupported_type"),
        (b"", "unsupported_type"),
        (png() + b"<script>alert(1)</script>", "active_content"),
        (png() + b"%PDF-1.7 hidden", "active_content"),
        (jpeg_with_gps()[:120], "malformed"),
        (png()[:40], "malformed"),
    ],
    ids=[
        "svg",
        "html",
        "exe",
        "empty",
        "polyglot-script",
        "polyglot-pdf",
        "truncated-jpeg",
        "truncated-png",
    ],
)
async def test_unsupported_active_and_broken_files_are_rejected_without_a_trace(
    data: bytes, reason: str, store: InMemoryObjectStore, executor: Executor, scratch: Path
) -> None:
    assert await rejected(make(store, executor, scratch), data) == reason
    assert_clean(store, scratch)


async def test_a_spoofed_declared_type_is_rejected(
    store: InMemoryObjectStore, executor: Executor, scratch: Path
) -> None:
    pipeline = make(store, executor, scratch)
    assert await rejected(pipeline, png(), declared_mime="application/pdf") == "spoofed_type"
    assert_clean(store, scratch)


async def test_the_size_cap_applies_while_streaming(
    store: InMemoryObjectStore, executor: Executor, scratch: Path
) -> None:
    consumed = 0

    async def endless() -> AsyncIterator[bytes]:
        nonlocal consumed
        while True:
            consumed += 1000
            yield b"\x89PNG" + b"0" * 996

    pipeline = make(store, executor, scratch)
    with pytest.raises(UploadRejectedError) as raised:
        await pipeline.process(endless(), filename="a.png")
    assert raised.value.reason == "too_large"
    assert consumed <= SMALL.max_file_bytes + 2000, "stopped reading soon after the cap"
    assert_clean(store, scratch)


async def test_a_decompression_bomb_is_rejected_by_pixel_count(
    store: InMemoryObjectStore, executor: Executor, scratch: Path
) -> None:
    bomb = png(3000, 3000)  # about 9 megapixels of white: tiny on disk, large in memory
    assert len(bomb) < 50_000
    assert await rejected(make(store, executor, scratch), bomb) == "too_many_pixels"
    assert_clean(store, scratch)


async def test_a_stream_that_fails_midway_leaves_no_temp_file(
    store: InMemoryObjectStore, executor: Executor, scratch: Path
) -> None:
    async def broken() -> AsyncIterator[bytes]:
        yield b"\x89PNG"
        raise ConnectionResetError

    with pytest.raises(ConnectionResetError):
        await make(store, executor, scratch).process(broken(), filename="a.png")
    assert_clean(store, scratch)


async def test_eicar_is_detected_and_nothing_is_stored(
    store: InMemoryObjectStore, executor: Executor, scratch: Path
) -> None:
    infected = png() + EICAR
    assert await rejected(make(store, executor, scratch), infected) == "malware_detected"
    assert_clean(store, scratch)


class FailingScanner:
    async def scan(self, data: bytes) -> str:
        del data
        raise UploadRejectedError("scan_failed")


async def test_a_scanner_failure_fails_closed(
    store: InMemoryObjectStore, executor: Executor, scratch: Path
) -> None:
    pipeline = make(store, executor, scratch, scanner=FailingScanner())
    assert await rejected(pipeline, png()) == "scan_failed"
    assert_clean(store, scratch)


async def test_the_demo_scanner_labels_files_not_scanned(
    store: InMemoryObjectStore, executor: Executor, scratch: Path
) -> None:
    pipeline = make(store, executor, scratch, scanner=NotDeployedScanner())
    result = await pipeline.process(stream(png()), filename="a.png")
    assert result.scan_state == "not_scanned_demo"


class RecordingScanner:
    def __init__(self) -> None:
        self.seen: list[bytes] = []

    async def scan(self, data: bytes) -> str:
        self.seen.append(data)
        return "clean"


async def test_both_the_raw_upload_and_the_stored_artifact_are_scanned(
    store: InMemoryObjectStore, executor: Executor, scratch: Path
) -> None:
    scanner = RecordingScanner()
    raw = jpeg_with_gps()
    result = await make(store, executor, scratch, scanner=scanner).process(
        stream(raw), filename="a.jpg"
    )
    assert scanner.seen == [raw, store.objects[result.object_key][0]]


class SlowStore(InMemoryObjectStore):
    async def put(self, key: str, data: bytes, content_type: str) -> None:
        await asyncio.sleep(5)
        await super().put(key, data, content_type)


async def test_a_storage_timeout_is_a_clean_failure(executor: Executor, scratch: Path) -> None:
    slow = SlowStore()
    limits = FileLimits(max_dimension=64, store_timeout_seconds=0.05)
    pipeline = make(slow, executor, scratch, limits=limits)
    assert await rejected(pipeline, png()) == "storage_failed"
    assert_clean(slow, scratch)


async def test_a_sanitiser_timeout_is_a_clean_failure(
    store: InMemoryObjectStore, scratch: Path
) -> None:
    with ThreadPoolExecutor(max_workers=1) as pool:
        blocker = pool.submit(time.sleep, 0.3)  # occupies the only worker
        limits = FileLimits(max_dimension=64, sanitise_timeout_seconds=0.05)
        reason = await rejected(make(store, pool, scratch, limits=limits), png())
        blocker.result()
    assert reason == "timeout"
    assert_clean(store, scratch)


async def test_pdfs_lose_metadata_scripts_and_attachments(
    store: InMemoryObjectStore, executor: Executor, scratch: Path
) -> None:
    result = await make(store, executor, scratch).process(
        stream(pdf_bytes(hostile=True)), filename="report.pdf", declared_mime="application/pdf"
    )
    stored = store.objects[result.object_key][0]
    for token in (b"JavaScript", b"OpenAction", b"EmbeddedFile", b"Canary Author", b"payload"):
        assert token not in stored
    with pikepdf.open(io.BytesIO(stored)) as reopened:
        assert len(reopened.pages) == 1


async def test_encrypted_and_long_pdfs_are_rejected(
    store: InMemoryObjectStore, executor: Executor, scratch: Path
) -> None:
    pipeline = make(store, executor, scratch)
    assert await rejected(pipeline, pdf_bytes(encrypt=True)) == "encrypted_pdf"
    assert await rejected(pipeline, pdf_bytes(pages=25)) == "too_many_pages"
    assert await rejected(pipeline, b"%PDF-1.7\ngarbage") == "malformed"
    assert_clean(store, scratch)


async def test_the_real_process_pool_sanitises_in_another_process(
    store: InMemoryObjectStore, scratch: Path
) -> None:
    with ProcessPoolExecutor(max_workers=1) as pool:
        result = await make(store, pool, scratch).process(stream(jpeg_with_gps()), filename="a.jpg")
    assert GPS_MARKER not in store.objects[result.object_key][0]


async def test_the_result_is_only_metadata_about_the_stored_copy(
    store: InMemoryObjectStore, executor: Executor, scratch: Path
) -> None:
    result = await make(store, executor, scratch).process(stream(png()), filename="a.png")
    assert isinstance(result, StoredEvidence)
    assert result.sanitation_state in vocabulary.values("evidence_sanitation_state")
    assert result.scan_state in vocabulary.values("malware_scan_state")


def test_sniffing_only_trusts_magic_bytes() -> None:
    assert sniff(b"\xff\xd8\xff\xe0") == "image/jpeg"
    assert sniff(b"RIFF\x00\x00\x00\x00WEBPVP8 ") == "image/webp"
    assert sniff(b"GIF89a") is None
    assert sniff(b"<svg") is None


def test_display_names_are_plain_and_carry_the_real_extension() -> None:
    assert safe_display_name("C:\\dir\\evil.svg", "image/png") == "evil.png"
    assert safe_display_name("../../.\x00..", "application/pdf") == "evidence.pdf"
    assert len(safe_display_name("a" * 500, "image/png")) <= 64


def test_object_keys_are_random_and_uniform() -> None:
    assert len({new_object_key() for _ in range(500)}) == 500


def test_the_startup_sweep_removes_stale_uploads(scratch: Path) -> None:
    (scratch / "sg-upload-abc").write_bytes(b"x")
    (scratch / "keep.txt").write_bytes(b"x")
    assert sweep_stale_uploads(scratch) == 1
    assert [p.name for p in scratch.iterdir()] == ["keep.txt"]


def test_the_hosted_demo_scanner_is_refused_in_production() -> None:
    with pytest.raises(ValueError, match="production"):
        build_scanner("not_deployed", app_env="production", host="h", port=1, timeout_seconds=1)
    demo = build_scanner("not_deployed", app_env="staging", host="h", port=1, timeout_seconds=1)
    assert isinstance(demo, NotDeployedScanner)
    real = build_scanner("clamd", app_env="production", host="h", port=1, timeout_seconds=1)
    assert isinstance(real, ClamdScanner)


async def clamd_server(reply: bytes | None) -> tuple[asyncio.Server, int, list[bytes]]:
    received: list[bytes] = []

    async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        received.append(await reader.readexactly(10))
        while (size := int.from_bytes(await reader.readexactly(4), "big")) > 0:
            received.append(await reader.readexactly(size))
        if reply is not None:
            writer.write(reply)
            await writer.drain()
        else:
            await asyncio.sleep(1)
        writer.close()

    server = await asyncio.start_server(handle, "127.0.0.1", 0)
    return server, server.sockets[0].getsockname()[1], received


@pytest.mark.parametrize(
    ("reply", "outcome"),
    [
        (b"stream: OK\0", "clean"),
        (b"stream: Eicar-Test-Signature FOUND\0", "malware_detected"),
        (b"INSTREAM size limit exceeded. ERROR\0", "scan_failed"),
        (None, "scan_failed"),
    ],
)
async def test_the_clamd_client_speaks_instream_and_fails_closed(
    reply: bytes | None, outcome: str
) -> None:
    server, port, received = await clamd_server(reply)
    async with server:
        scanner = ClamdScanner("127.0.0.1", port, timeout_seconds=0.3)
        payload = b"a" * 100_000
        if outcome == "clean":
            assert await scanner.scan(payload) == "clean"
            assert received[0] == b"zINSTREAM\0"
            assert b"".join(received[1:]) == payload
        else:
            with pytest.raises(UploadRejectedError) as raised:
                await scanner.scan(payload)
            assert raised.value.reason == outcome


async def test_a_refused_clamd_connection_fails_closed() -> None:
    scanner = ClamdScanner("127.0.0.1", 1, timeout_seconds=0.3)
    with pytest.raises(UploadRejectedError) as raised:
        await scanner.scan(b"x")
    assert raised.value.reason == "scan_failed"
