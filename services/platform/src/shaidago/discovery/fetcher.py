"""The public-page fetcher: safe by construction, bounded in every dimension.

Each hop resolves the host, requires every address to be public, and connects to a validated IP
directly (with the original ``Host`` header and TLS server name), so a DNS answer that changes
between check and use cannot redirect the connection. Redirects are followed by hand, each one
re-parsed and re-validated. Only a fixed set of request headers is ever sent: no cookies, no
credentials, nothing from the caller. The body is streamed under a compressed-byte cap and a
decompressed-byte cap, both bounded by an overall deadline. ``robots.txt`` and access controls are
honoured, never bypassed.
"""

import asyncio
import time
import zlib
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Final
from urllib.parse import urljoin
from urllib.robotparser import RobotFileParser

import httpx

from shaidago.discovery.netguard import (
    Resolver,
    Target,
    parse_target,
    resolve_public,
)

USER_AGENT: Final = "ShaidaGoScout/1.0 (public civic-information research; +respects-robots-txt)"
ROBOTS_AGENT: Final = "ShaidaGoScout"
ALLOWED_CONTENT_TYPES: Final = frozenset(
    {"text/html", "application/xhtml+xml", "text/plain", "application/pdf"}
)
ALLOWED_ENCODINGS: Final = frozenset({"", "identity", "gzip", "deflate"})
ACCESS_STATUSES: Final = frozenset({401, 402, 403, 407, 451})
REDIRECT_STATUSES: Final = frozenset({301, 302, 303, 307, 308})
_CHALLENGE_MARKERS: Final = (b"g-recaptcha", b"hcaptcha", b"cf-challenge", b"captcha")
_LOGIN_MARKER: Final = b'type="password"'
_OK: Final = 200
_CLIENT_ERROR: Final = 400
_SERVER_ERROR: Final = 500
_SNIFF_BYTES: Final = 8192
_DECOMPRESS_STEP: Final = 65536


class FetchError(Exception):
    """A page was not fetched. ``code`` is a stable, content-free reason."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class FetchLimits:
    max_redirects: int = 3
    connect_timeout: float = 5.0
    read_timeout: float = 8.0
    total_timeout: float = 15.0
    max_raw_bytes: int = 2_000_000
    max_body_bytes: int = 2_000_000
    per_host_concurrency: int = 2
    per_host_interval: float = 1.0
    max_robots_bytes: int = 200_000


@dataclass(frozen=True)
class FetchedPage:
    final_url: str
    status: int
    content_type: str
    body: bytes


ClientFactory = Callable[[], httpx.AsyncClient]
Sleep = Callable[[float], Awaitable[None]]


def default_client_factory(limits: FetchLimits) -> ClientFactory:
    timeout = httpx.Timeout(limits.read_timeout, connect=limits.connect_timeout)

    def build() -> httpx.AsyncClient:
        # A fresh client per hop: no cookie jar survives, and redirects are never automatic.
        return httpx.AsyncClient(timeout=timeout, follow_redirects=False, trust_env=False)

    return build


class HostPacer:
    """Per-host concurrency and minimum spacing, so a page is never hammered."""

    def __init__(self, limits: FetchLimits, sleep: Sleep = asyncio.sleep) -> None:
        self._limits = limits
        self._sleep = sleep
        self._gates: dict[str, asyncio.Semaphore] = {}
        self._last: dict[str, float] = {}

    async def wait(self, host: str) -> asyncio.Semaphore:
        gate = self._gates.setdefault(host, asyncio.Semaphore(self._limits.per_host_concurrency))
        await gate.acquire()
        delay = self._last.get(host, 0.0) + self._limits.per_host_interval - time.monotonic()
        if delay > 0:
            await self._sleep(delay)
        self._last[host] = time.monotonic()
        return gate


class SafeFetcher:
    def __init__(
        self,
        resolver: Resolver,
        *,
        limits: FetchLimits | None = None,
        client_factory: ClientFactory | None = None,
        sleep: Sleep = asyncio.sleep,
    ) -> None:
        self._resolver = resolver
        self._limits = limits or FetchLimits()
        self._factory = client_factory or default_client_factory(self._limits)
        self._pacer = HostPacer(self._limits, sleep)
        self._robots: dict[str, RobotFileParser | None] = {}

    async def fetch(self, url: str) -> FetchedPage:
        """Fetch one public page or raise ``FetchError`` / ``UnsafeDestinationError``."""
        try:
            async with asyncio.timeout(self._limits.total_timeout):
                return await self._follow(url)
        except TimeoutError:
            raise FetchError("timeout") from None

    async def _follow(self, url: str) -> FetchedPage:
        current = url
        for _ in range(self._limits.max_redirects + 1):
            target = parse_target(current)
            await self._check_robots(target)
            response = await self._hop(target)
            if isinstance(response, str):
                current = urljoin(current, response)
                continue
            return response
        raise FetchError("too_many_redirects")

    async def _hop(self, target: Target) -> FetchedPage | str:
        """One validated request. Returns the page, or the ``Location`` of a redirect."""
        addresses = await resolve_public(target, self._resolver)
        gate = await self._pacer.wait(target.host)
        try:
            last: Exception | None = None
            for address in addresses[:2]:
                try:
                    return await self._request(target, address, robots=False)
                except httpx.HTTPError as error:
                    last = error
            raise FetchError("connection_failed") from last
        finally:
            gate.release()

    async def _request(self, target: Target, address: str, *, robots: bool) -> FetchedPage | str:
        host_for_url = f"[{address}]" if ":" in address else address
        pinned = f"{target.scheme}://{host_for_url}:{target.port}{target.path}"
        headers = {
            "Host": target.host if target.port in {80, 443} else f"{target.host}:{target.port}",
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,text/plain,application/pdf;q=0.9",
            "Accept-Encoding": "gzip, deflate",
        }
        extensions = {"sni_hostname": target.host} if target.scheme == "https" else {}
        async with (
            self._factory() as client,
            client.stream("GET", pinned, headers=headers, extensions=extensions) as r,
        ):
            return await self._read(target, r, robots=robots)

    async def _read(
        self, target: Target, response: httpx.Response, *, robots: bool
    ) -> FetchedPage | str:
        status = response.status_code
        if status in REDIRECT_STATUSES:
            location = response.headers.get("location")
            if not location:
                raise FetchError("bad_redirect")
            return location
        if status in ACCESS_STATUSES or "www-authenticate" in response.headers:
            raise FetchError("access_restricted")
        content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        if robots:
            limit = self._limits.max_robots_bytes
        else:
            if status == _OK and content_type not in ALLOWED_CONTENT_TYPES:
                raise FetchError("unsupported_content_type")
            limit = self._limits.max_body_bytes
        encoding = response.headers.get("content-encoding", "").strip().lower()
        if encoding not in ALLOWED_ENCODINGS:
            raise FetchError("unsupported_encoding")
        declared = response.headers.get("content-length")
        if (
            declared is not None
            and declared.isdigit()
            and int(declared) > self._limits.max_raw_bytes
        ):
            raise FetchError("too_large")
        body = await self._body(response, encoding, limit)
        if not robots and status != _OK:
            raise FetchError("http_status")
        if not robots and _challenge_or_login(body, content_type):
            raise FetchError("access_restricted")
        return FetchedPage(f"{target.origin}{target.path}", status, content_type, body)

    async def _body(self, response: httpx.Response, encoding: str, limit: int) -> bytes:
        decoder = None if encoding in {"", "identity"} else zlib.decompressobj(wbits=47)
        raw_total = 0
        out = bytearray()
        async for chunk in _guard(response.aiter_raw(), self._limits.max_raw_bytes):
            raw_total += len(chunk)
            if decoder is None:
                out += chunk
            else:
                out += _inflate(decoder, chunk, limit - len(out))
            if len(out) > limit:
                raise FetchError("too_large")
        if decoder is not None:
            out += _inflate(decoder, b"", limit - len(out), final=True)
        if len(out) > limit:
            raise FetchError("too_large")
        return bytes(out)

    async def _check_robots(self, target: Target) -> None:
        origin = target.origin
        if origin not in self._robots:
            self._robots[origin] = await self._load_robots(target)
        parser = self._robots[origin]
        if parser is None:
            raise FetchError("robots_disallowed")  # robots.txt unavailable: assume disallowed
        if not parser.can_fetch(ROBOTS_AGENT, f"{origin}{target.path}"):
            raise FetchError("robots_disallowed")

    async def _load_robots(self, target: Target) -> RobotFileParser | None:
        robots_target = Target(
            target.scheme, target.host, target.port, "/robots.txt", target.is_ip_literal
        )
        addresses = await resolve_public(robots_target, self._resolver)
        gate = await self._pacer.wait(target.host)
        parser = RobotFileParser()
        try:
            page = await self._request(robots_target, addresses[0], robots=True)
        except httpx.HTTPError, FetchError:
            return None
        finally:
            gate.release()
        if isinstance(page, str):
            return None  # a redirecting robots.txt is treated as unavailable
        if page.status >= _SERVER_ERROR:
            return None
        if page.status >= _CLIENT_ERROR:
            parser.parse([])  # no robots.txt (4xx): everything is allowed
            return parser
        parser.parse(page.body.decode("utf-8", "replace").splitlines())
        return parser


async def _guard(stream: AsyncIterator[bytes], max_raw: int) -> AsyncIterator[bytes]:
    total = 0
    async for chunk in stream:
        total += len(chunk)
        if total > max_raw:
            raise FetchError("too_large")
        yield chunk


def _inflate(decoder: Any, chunk: bytes, room: int, *, final: bool = False) -> bytes:
    """Decompress ``chunk`` producing at most ``room + 1`` bytes, so a bomb is caught early."""
    out = bytearray()
    try:
        data = chunk
        while True:
            produced = decoder.decompress(data, max(room - len(out), 0) + 1)
            out += produced
            if len(out) > room or not decoder.unconsumed_tail:
                break
            data = decoder.unconsumed_tail
        if final:
            out += decoder.flush()
    except zlib.error:
        raise FetchError("bad_encoding") from None
    return bytes(out)


def _challenge_or_login(body: bytes, content_type: str) -> bool:
    if content_type not in {"text/html", "application/xhtml+xml"}:
        return False
    head = body[:_SNIFF_BYTES].lower()
    return _LOGIN_MARKER in head or any(marker in head for marker in _CHALLENGE_MARKERS)
