"""The safe fetcher against a simulated network: pinning, redirects, bombs, slow bodies, robots."""

import asyncio
import gzip
import zlib
from collections.abc import AsyncIterator, Callable

import httpx
import pytest

from shaidago.discovery.fetcher import (
    FetchedPage,
    FetchError,
    FetchLimits,
    SafeFetcher,
    default_client_factory,
)
from shaidago.discovery.netguard import UnsafeDestinationError

PUBLIC_A = "93.184.216.34"
HTML = b"<html><body><p>Synthetic public page.</p></body></html>"
Handler = Callable[[httpx.Request], httpx.Response]


class Dns:
    """A resolver that answers from a table and counts how often it is asked."""

    def __init__(self, table: dict[str, list[str] | list[list[str]]]) -> None:
        self.table = table
        self.calls: list[str] = []

    async def resolve(self, host: str) -> list[str]:
        self.calls.append(host)
        answer = self.table[host]
        if answer and isinstance(answer[0], list):  # a sequence of answers, one per lookup
            sequence: list[list[str]] = answer  # type: ignore[assignment]
            index = min(self.calls.count(host) - 1, len(sequence) - 1)
            return sequence[index]
        return answer  # type: ignore[return-value]


def fetcher(
    handler: Handler | Callable[[httpx.Request], object],
    dns: Dns | None = None,
    **limits: float,
) -> tuple[SafeFetcher, list[httpx.Request], Dns]:
    seen: list[httpx.Request] = []
    resolver = dns or Dns({"example.test": [PUBLIC_A], "other.test": ["8.8.8.8"]})

    async def wrapped(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        result = handler(request)
        if asyncio.iscoroutine(result):
            result = await result
        assert isinstance(result, httpx.Response)
        if result.is_stream_consumed:  # built with content=: hand it back as a fresh stream
            result = httpx.Response(
                result.status_code, headers=result.headers, stream=httpx.ByteStream(result.content)
            )
        return result

    def factory() -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=httpx.MockTransport(wrapped))

    config = FetchLimits(per_host_interval=0.0, **limits)  # type: ignore[arg-type]

    async def no_sleep(_seconds: float) -> None:
        return None

    return (
        SafeFetcher(resolver, limits=config, client_factory=factory, sleep=no_sleep),
        seen,
        resolver,
    )


def serve(page: httpx.Response, robots: httpx.Response | None = None) -> Handler:
    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return robots or httpx.Response(404)
        return page

    return handle


def empty(status: int) -> httpx.Response:
    return httpx.Response(status, stream=httpx.ByteStream(b""))


def html(body: bytes = HTML, **headers: str) -> httpx.Response:
    return httpx.Response(
        200,
        stream=httpx.ByteStream(body),
        headers={"content-type": "text/html; charset=utf-8", **headers},
    )


async def test_a_public_page_is_fetched_over_a_pinned_ip_with_only_fixed_headers() -> None:
    fetch, seen, _ = fetcher(serve(html()))
    page = await fetch.fetch("https://example.test/report?id=1")
    assert isinstance(page, FetchedPage)
    assert (page.status, page.content_type, page.body) == (200, "text/html", HTML)
    assert page.final_url == "https://example.test:443/report?id=1"
    for request in seen:
        assert request.url.host == PUBLIC_A  # connected to the validated address, not the name
        assert request.headers["host"] == "example.test"
        assert request.extensions["sni_hostname"] == "example.test"
        assert set(request.headers) <= {
            "host",
            "user-agent",
            "accept",
            "accept-encoding",
            "connection",
        }
    assert {r.url.path for r in seen} == {"/robots.txt", "/report"}


async def test_dns_rebinding_between_lookups_cannot_reach_a_private_address() -> None:
    dns = Dns({"example.test": [[PUBLIC_A], ["127.0.0.1"]]})  # public for robots, private after
    fetch, seen, _ = fetcher(serve(html()), dns)
    with pytest.raises(UnsafeDestinationError) as raised:
        await fetch.fetch("http://example.test/")
    assert raised.value.code == "private_address"
    assert all(r.url.host == PUBLIC_A for r in seen)
    assert {r.url.path for r in seen} == {"/robots.txt"}
    assert dns.calls == ["example.test", "example.test"]


@pytest.mark.parametrize(
    "answer", [[PUBLIC_A, "10.0.0.5"], ["::1"], ["169.254.169.254"], ["fd00:ec2::254"]]
)
async def test_mixed_or_private_dns_answers_refuse_the_host(answer: list[str]) -> None:
    fetch, seen, _ = fetcher(serve(html()), Dns({"example.test": answer}))
    with pytest.raises(UnsafeDestinationError):
        await fetch.fetch("http://example.test/")
    assert seen == []


@pytest.mark.parametrize(
    "location",
    [
        "http://127.0.0.1/",
        "http://169.254.169.254/latest/meta-data/",
        "http://[::1]/",
        "http://2130706433/",
        "http://user:pw@other.test/",
        "ftp://other.test/file",
        "http://other.test:8080/",
        "file:///etc/passwd",
        "http://localhost/",
    ],
)
async def test_a_redirect_to_an_unsafe_destination_is_refused(location: str) -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(302, headers={"location": location})

    fetch, seen, _ = fetcher(handle)
    with pytest.raises(UnsafeDestinationError):
        await fetch.fetch("http://example.test/start")
    assert {r.url.host for r in seen} == {PUBLIC_A}


async def test_a_redirect_to_a_hostname_that_resolves_privately_is_refused() -> None:
    dns = Dns({"example.test": [PUBLIC_A], "internal.test": ["10.1.2.3"]})

    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(301, headers={"location": "http://internal.test/admin"})

    fetch, seen, _ = fetcher(handle, dns)
    with pytest.raises(UnsafeDestinationError):
        await fetch.fetch("http://example.test/")
    assert all(r.url.host == PUBLIC_A for r in seen)


async def test_safe_redirects_are_followed_and_revalidated_within_a_limit() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        host = request.headers["host"]
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        if request.url.path == "/start":
            return httpx.Response(302, headers={"location": "/next"})
        if request.url.path == "/next":
            return httpx.Response(302, headers={"location": "https://other.test/final"})
        assert host == "other.test"
        return html()

    fetch, _, dns = fetcher(handle)
    page = await fetch.fetch("http://example.test/start")
    assert page.final_url == "https://other.test:443/final"
    assert dns.calls.count("other.test") >= 1

    def loop(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(302, headers={"location": "/again"})

    looping, _, _ = fetcher(loop)
    with pytest.raises(FetchError) as raised:
        await looping.fetch("http://example.test/")
    assert raised.value.code == "too_many_redirects"
    bad, _, _ = fetcher(lambda r: httpx.Response(404 if r.url.path == "/robots.txt" else 302))
    with pytest.raises(FetchError) as no_location:
        await bad.fetch("http://example.test/")
    assert no_location.value.code == "bad_redirect"


async def test_cookies_and_credentials_are_never_forwarded() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        assert "cookie" not in request.headers
        assert "authorization" not in request.headers
        if request.url.path == "/robots.txt":
            return httpx.Response(404, headers={"set-cookie": "sid=1"})
        if request.url.path == "/a":
            return httpx.Response(302, headers={"location": "/b", "set-cookie": "sid=abc"})
        return html()

    fetch, seen, _ = fetcher(handle)
    await fetch.fetch("http://example.test/a")
    assert len(seen) == 3


async def test_a_declared_or_streamed_body_over_the_cap_is_refused() -> None:
    declared, _, _ = fetcher(
        serve(html(b"x", **{"content-length": "999999999"})), max_raw_bytes=1000
    )
    with pytest.raises(FetchError) as one:
        await declared.fetch("http://example.test/")
    assert one.value.code == "too_large"

    async def chunks() -> AsyncIterator[bytes]:
        for _ in range(100):
            yield b"a" * 100

    streamed, _, _ = fetcher(
        serve(httpx.Response(200, headers={"content-type": "text/html"}, stream=_Stream(chunks))),
        max_raw_bytes=500,
        max_body_bytes=500,
    )
    with pytest.raises(FetchError) as two:
        await streamed.fetch("http://example.test/")
    assert two.value.code == "too_large"


class _Stream(httpx.AsyncByteStream):
    def __init__(self, factory: Callable[[], AsyncIterator[bytes]]) -> None:
        self._factory = factory

    async def __aiter__(self) -> AsyncIterator[bytes]:
        async for chunk in self._factory():
            yield chunk


@pytest.mark.parametrize("codec", ["gzip", "deflate"])
async def test_a_compression_bomb_is_stopped_at_the_decompressed_cap(codec: str) -> None:
    bomb = (
        gzip.compress(b"\0" * 50_000_000) if codec == "gzip" else zlib.compress(b"\0" * 50_000_000)
    )
    assert len(bomb) < 100_000
    fetch, _, _ = fetcher(
        serve(html(bomb, **{"content-encoding": codec})),
        max_raw_bytes=200_000,
        max_body_bytes=200_000,
    )
    with pytest.raises(FetchError) as raised:
        await fetch.fetch("http://example.test/")
    assert raised.value.code == "too_large"


async def test_ordinary_compression_is_decoded_and_unknown_or_corrupt_encodings_refused() -> None:
    fine, _, _ = fetcher(serve(html(gzip.compress(HTML), **{"content-encoding": "gzip"})))
    assert (await fine.fetch("http://example.test/")).body == HTML
    for encoding, body, code in (
        ("br", b"x", "unsupported_encoding"),
        ("gzip", b"not gzip", "bad_encoding"),
        ("zstd", b"x", "unsupported_encoding"),
    ):
        fetch, _, _ = fetcher(serve(html(body, **{"content-encoding": encoding})))
        with pytest.raises(FetchError) as raised:
            await fetch.fetch("http://example.test/")
        assert raised.value.code == code


async def test_a_slowly_dripping_body_hits_the_total_deadline() -> None:
    async def drip() -> AsyncIterator[bytes]:
        for _ in range(100):
            await asyncio.sleep(0.05)
            yield b"a"

    fetch, _, _ = fetcher(
        serve(httpx.Response(200, headers={"content-type": "text/html"}, stream=_Stream(drip))),
        total_timeout=0.2,
    )
    with pytest.raises(FetchError) as raised:
        await fetch.fetch("http://example.test/")
    assert raised.value.code == "timeout"


@pytest.mark.parametrize(
    ("response", "code"),
    [
        (
            httpx.Response(200, content=b"PK", headers={"content-type": "application/zip"}),
            "unsupported_content_type",
        ),
        (
            httpx.Response(200, content=b"x", headers={"content-type": "application/octet-stream"}),
            "unsupported_content_type",
        ),
        (httpx.Response(200, content=b"x"), "unsupported_content_type"),
        (httpx.Response(404, content=b"", headers={"content-type": "text/html"}), "http_status"),
        (httpx.Response(500, content=b"", headers={"content-type": "text/html"}), "http_status"),
        (httpx.Response(401), "access_restricted"),
        (httpx.Response(402), "access_restricted"),
        (httpx.Response(403), "access_restricted"),
        (httpx.Response(451), "access_restricted"),
        (
            httpx.Response(
                200,
                content=b"x",
                headers={"content-type": "text/html", "www-authenticate": "Basic"},
            ),
            "access_restricted",
        ),
        (html(b"<div class='g-recaptcha'></div>"), "access_restricted"),
        (html(b"<script src='https://x/hcaptcha.js'></script>"), "access_restricted"),
        (html(b'<form><input type="password" name="p"></form>'), "access_restricted"),
    ],
)
async def test_unsupported_types_errors_and_access_barriers_are_reported_not_bypassed(
    response: httpx.Response, code: str
) -> None:
    fetch, _, _ = fetcher(serve(response))
    with pytest.raises(FetchError) as raised:
        await fetch.fetch("http://example.test/")
    assert raised.value.code == code


async def test_a_pdf_and_plain_text_are_allowed() -> None:
    for content_type in ("application/pdf", "text/plain"):
        fetch, _, _ = fetcher(
            serve(httpx.Response(200, content=b"data", headers={"content-type": content_type}))
        )
        assert (await fetch.fetch("http://example.test/x")).content_type == content_type


async def test_robots_txt_is_honoured_and_cached_per_origin() -> None:
    robots = httpx.Response(200, text="User-agent: *\nDisallow: /private\n")
    fetch, seen, _ = fetcher(serve(html(), robots))
    await fetch.fetch("http://example.test/public")
    with pytest.raises(FetchError) as blocked:
        await fetch.fetch("http://example.test/private/report")
    assert blocked.value.code == "robots_disallowed"
    assert [r.url.path for r in seen].count("/robots.txt") == 1
    assert "/private/report" not in [r.url.path for r in seen]


async def test_our_agent_can_be_named_and_a_full_disallow_blocks_everything() -> None:
    robots = httpx.Response(200, text="User-agent: ShaidaGoScout\nDisallow: /\n")
    fetch, seen, _ = fetcher(serve(html(), robots))
    with pytest.raises(FetchError) as raised:
        await fetch.fetch("http://example.test/")
    assert raised.value.code == "robots_disallowed"
    assert [r.url.path for r in seen] == ["/robots.txt"]


@pytest.mark.parametrize(
    "robots",
    [httpx.Response(500), httpx.Response(503), httpx.Response(302, headers={"location": "/x"})],
)
async def test_an_unavailable_robots_txt_means_do_not_fetch(robots: httpx.Response) -> None:
    fetch, seen, _ = fetcher(serve(html(), robots))
    with pytest.raises(FetchError) as raised:
        await fetch.fetch("http://example.test/")
    assert raised.value.code == "robots_disallowed"
    assert {r.url.path for r in seen} == {"/robots.txt"}


async def test_a_missing_robots_txt_allows_fetching() -> None:
    fetch, _, _ = fetcher(serve(html(), httpx.Response(404)))
    assert (await fetch.fetch("http://example.test/")).status == 200


async def test_a_connection_failure_is_reported_generically() -> None:
    def down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    fetch, _, _ = fetcher(down)
    with pytest.raises(FetchError) as raised:
        await fetch.fetch("http://example.test/")
    assert raised.value.code == "robots_disallowed"  # robots.txt could not be read either


async def test_requests_to_one_host_are_spaced_out() -> None:
    sleeps: list[float] = []

    async def record(seconds: float) -> None:
        sleeps.append(seconds)

    resolver = Dns({"example.test": [PUBLIC_A]})
    limits = FetchLimits(per_host_interval=5.0)

    def handle(request: httpx.Request) -> httpx.Response:
        return empty(404) if request.url.path == "/robots.txt" else html()

    def factory() -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=httpx.MockTransport(handle))

    fetch = SafeFetcher(resolver, limits=limits, client_factory=factory, sleep=record)
    await fetch.fetch("http://example.test/a")
    assert any(0 < s <= 5.0 for s in sleeps)  # the second request (page after robots) waited


async def test_a_refused_connection_to_the_page_is_reported_generically() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return empty(404)
        raise httpx.ConnectError("refused", request=request)

    fetch, _, _ = fetcher(handle)
    with pytest.raises(FetchError) as raised:
        await fetch.fetch("http://example.test/")
    assert raised.value.code == "connection_failed"


async def test_the_default_client_never_follows_redirects_or_reads_the_environment() -> None:
    async with default_client_factory(FetchLimits())() as client:
        assert client.follow_redirects is False
        assert client.timeout.connect == 5.0
        assert len(client.cookies.jar) == 0
