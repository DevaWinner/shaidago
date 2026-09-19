"""Destination validation: every ambiguous, private, and unsupported form is refused."""

import asyncio
import socket
from typing import Any

import pytest

from shaidago.discovery.netguard import (
    SystemResolver,
    UnsafeDestinationError,
    canonical_host,
    is_public_address,
    parse_target,
    resolve_public,
)

REFUSED = {
    "http://127.0.0.1/": "private_address",  # parses; refused at resolution
    "http://localhost/": "blocked_host",
    "http://LOCALHOST./": "blocked_host",
    "http://app.localhost/": "blocked_host",
    "http://2130706433/": "ambiguous_ip",
    "http://0177.0.0.1/": "ambiguous_ip",
    "http://0x7f.0.0.1/": "ambiguous_ip",
    "http://0x7f000001/": "ambiguous_ip",
    "http://127.1/": "ambiguous_ip",
    "http://1.2.3/": "ambiguous_ip",
    "http://010.0.0.1/": "ambiguous_ip",
    "http://[::ffff:7f00:1]/": "private_address",
    "http://[::1]/": "private_address",
    "http://[fe80::1]/": "private_address",
    "http://[fd00:ec2::254]/": "private_address",
    "http://[64:ff9b::7f00:1]/": "private_address",
    "http://[2002:7f00:1::]/": "private_address",
    "http://169.254.169.254/latest/meta-data/": "private_address",
    "http://metadata.google.internal/": "blocked_host",
    "http://printer.local/": "blocked_host",
    "http://intranet/": "blocked_host",
    "http://user:pass@example.test/": "credentials_in_url",
    "http://example.test@127.0.0.1/": "credentials_in_url",
    "http://:@example.test/": "credentials_in_url",
    "ftp://example.test/": "unsupported_scheme",
    "file:///etc/passwd": "unsupported_scheme",
    "gopher://example.test/": "unsupported_scheme",
    "javascript:alert(1)": "unsupported_scheme",
    "http://example.test:8080/": "unsupported_port",
    "https://example.test:8443/": "unsupported_port",
    "http://example.test:22/": "unsupported_port",
    "http://example.test:99999/": "malformed_url",
    "http:///path": "malformed_url",
    "": "malformed_url",
    "http://exa mple.test/": "malformed_url",
    "http://example.test/\x00": "malformed_url",
    "http://example.test/" + "a" * 3000: "malformed_url",
    "http://-bad-.test/": "blocked_host",
    "http://exa_mple.test/": "blocked_host",
    "http://a..b.test/": "malformed_url",
    "http://1.2.3.4.5/": "ambiguous_ip",
}


@pytest.mark.parametrize(("url", "code"), list(REFUSED.items()))
async def test_every_unsafe_form_is_refused_with_a_stable_code(url: str, code: str) -> None:
    class Never:
        async def resolve(self, host: str) -> list[str]:  # pragma: no cover - IP literals only
            raise AssertionError(host)

    async def check() -> None:
        await resolve_public(parse_target(url), Never())

    with pytest.raises(UnsafeDestinationError) as raised:
        await check()
    assert raised.value.code == code
    assert not url or url not in str(raised.value)


def test_safe_urls_parse_to_a_canonical_target() -> None:
    plain = parse_target("HTTPS://Example.TEST./a/b?x=1#frag")
    assert (plain.scheme, plain.host, plain.port, plain.path) == (
        "https",
        "example.test",
        443,
        "/a/b?x=1",
    )
    assert parse_target("http://example.test").path == "/"
    assert parse_target("http://example.test:443/").port == 443
    assert parse_target("http://8.8.8.8/x").is_ip_literal
    assert parse_target("http://[2606:4700:4700::1111]/").host == "2606:4700:4700::1111"
    assert parse_target("http://bücher.example/").host == "xn--bcher-kva.example"


PRIVATE = [
    "10.0.0.1", "172.16.0.1", "172.31.255.255", "192.168.1.1", "127.0.0.1", "127.255.255.254",
    "100.64.0.1", "198.18.0.1", "198.19.255.255", "192.0.2.1", "198.51.100.7", "203.0.113.5",
    "192.0.0.1", "240.0.0.1", "255.255.255.255", "224.0.0.1", "0.0.0.0", "169.254.169.254",  # noqa: S104
    "::", "::1", "fe80::1", "fc00::1", "fd12::1", "ff02::1", "2001:db8::1", "64:ff9b::a00:1",
    "2002:a00:1::", "2001:0:4136:e378:8000:63bf:3fff:fdd2", "::ffff:10.0.0.1", "::ffff:127.0.0.1",
    "fd00:ec2::254", "not-an-ip", "", "1.2.3",
]  # fmt: skip
PUBLIC = ["8.8.8.8", "1.1.1.1", "93.184.216.34", "2606:4700:4700::1111", "::ffff:8.8.8.8"]


@pytest.mark.parametrize("address", PRIVATE)
def test_private_reserved_and_embedded_addresses_are_not_public(address: str) -> None:
    assert not is_public_address(address)


@pytest.mark.parametrize("address", PUBLIC)
def test_global_addresses_are_public(address: str) -> None:
    assert is_public_address(address)


class Fixed:
    def __init__(self, addresses: list[str]) -> None:
        self.addresses = addresses

    async def resolve(self, host: str) -> list[str]:
        del host
        return self.addresses


async def test_a_host_is_safe_only_if_every_resolved_address_is_public() -> None:
    target = parse_target("http://example.test/")
    assert await resolve_public(target, Fixed(["8.8.8.8", "2606:4700:4700::1111"])) == [
        "8.8.8.8",
        "2606:4700:4700::1111",
    ]
    for mixed in (["8.8.8.8", "10.0.0.1"], ["8.8.8.8", "::1"], ["169.254.169.254"]):
        with pytest.raises(UnsafeDestinationError) as raised:
            await resolve_public(target, Fixed(mixed))
        assert raised.value.code == "private_address"
    with pytest.raises(UnsafeDestinationError) as empty:
        await resolve_public(target, Fixed([]))
    assert empty.value.code == "dns_failure"


async def test_a_public_ip_literal_skips_the_resolver() -> None:
    target = parse_target("http://8.8.8.8/")
    assert await resolve_public(target, Fixed(["10.0.0.1"])) == ["8.8.8.8"]


def test_a_malformed_ipv6_host_is_ambiguous() -> None:

    with pytest.raises(UnsafeDestinationError) as raised:
        canonical_host("a:b")
    assert raised.value.code == "ambiguous_ip"
    with pytest.raises(UnsafeDestinationError):
        canonical_host(None)


async def test_the_system_resolver_returns_every_address_and_hides_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake(_self: object, host: str, *_a: object, **_k: object) -> list[Any]:
        del host
        return [
            (socket.AF_INET, 1, 6, "", ("8.8.8.8", 0)),
            (socket.AF_INET, 1, 6, "", ("8.8.8.8", 0)),
            (socket.AF_INET6, 1, 6, "", ("::1", 0, 0, 0)),
        ]

    loop = asyncio.get_running_loop()
    monkeypatch.setattr(type(loop), "getaddrinfo", fake)
    assert await SystemResolver().resolve("example.test") == ["8.8.8.8", "::1"]

    async def failing(_self: object, host: str, *_a: object, **_k: object) -> list[object]:
        raise OSError(host)

    monkeypatch.setattr(type(loop), "getaddrinfo", failing)
    with pytest.raises(UnsafeDestinationError) as raised:
        await SystemResolver().resolve("example.test")
    assert raised.value.code == "dns_failure"
    assert "example.test" not in str(raised.value)
