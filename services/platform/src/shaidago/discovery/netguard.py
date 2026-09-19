"""Destination validation from primitives: parse strictly, resolve, and judge every address.

A URL regex is not a defence. This module accepts a URL only if it parses to exactly one plain
hostname (or one canonical IP literal) on port 80 or 443 with no credentials, refuses every
ambiguous IP spelling (decimal, octal, hex, shorthand), and treats a hostname as safe only if
*every* address it resolves to is globally routable. Embedded-IPv4 forms (IPv4-mapped, NAT64,
6to4, Teredo) are unwrapped or refused, so a private target cannot hide inside an IPv6 address.
"""

import asyncio
import ipaddress
import re
import socket
from dataclasses import dataclass
from typing import Final, Protocol
from urllib.parse import urlsplit

ALLOWED_PORTS: Final = {"http": 80, "https": 443}
MAX_URL_CHARS: Final = 2048
_NUMERICISH: Final = re.compile(r"^[0-9a-fx.]+$", re.I)
_LABEL: Final = re.compile(r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$")
_BLOCKED_SUFFIXES: Final = (".localhost", ".local", ".internal", ".home.arpa", ".lan", ".corp")
_BLOCKED_NETWORKS: Final = tuple(
    ipaddress.ip_network(n)
    for n in (
        "64:ff9b::/96",  # NAT64: embeds an IPv4 target
        "64:ff9b:1::/48",
        "2002::/16",  # 6to4
        "2001::/32",  # Teredo
        "100.64.0.0/10",  # carrier-grade NAT
        "192.0.0.0/24",
        "198.18.0.0/15",
        "fd00:ec2::/32",  # cloud metadata (IPv6)
        "169.254.0.0/16",  # link-local and cloud metadata (IPv4)
    )
)


class UnsafeDestinationError(Exception):
    """A URL or address was refused. ``code`` is stable; the URL is never included."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class Target:
    scheme: str
    host: str  # lower-case ASCII (IDNA) hostname, or a canonical IP literal
    port: int
    path: str  # path and query, always starting with "/"
    is_ip_literal: bool

    @property
    def origin(self) -> str:
        return f"{self.scheme}://{self.host}:{self.port}"


class Resolver(Protocol):
    async def resolve(self, host: str) -> list[str]:
        """Every A and AAAA address for ``host``."""
        ...


class SystemResolver:
    async def resolve(self, host: str) -> list[str]:
        loop = asyncio.get_running_loop()
        try:
            infos = await loop.getaddrinfo(host, None, type=socket.SOCK_STREAM)
        except OSError:
            raise UnsafeDestinationError("dns_failure") from None
        return sorted({str(info[4][0]) for info in infos})


def is_public_address(address: str) -> bool:
    """True only for a globally routable address that does not embed a private target."""
    try:
        ip = ipaddress.ip_address(address.split("%", 1)[0])
    except ValueError:
        return False
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        return is_public_address(str(ip.ipv4_mapped))
    if any(ip in network for network in _BLOCKED_NETWORKS if network.version == ip.version):
        return False
    return ip.is_global and not (ip.is_multicast or ip.is_reserved or ip.is_unspecified)


def parse_target(url: str) -> Target:
    """A safe, canonical target, or ``UnsafeDestinationError`` with a stable code."""
    if not url or len(url) > MAX_URL_CHARS or any(ord(c) < 33 or ord(c) == 127 for c in url):  # noqa: PLR2004
        raise UnsafeDestinationError("malformed_url")
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError:
        raise UnsafeDestinationError("malformed_url") from None
    scheme = parts.scheme.lower()
    if scheme not in ALLOWED_PORTS:
        raise UnsafeDestinationError("unsupported_scheme")
    if "@" in parts.netloc or parts.username is not None or parts.password is not None:
        raise UnsafeDestinationError("credentials_in_url")
    if port is not None and port != ALLOWED_PORTS[scheme] and port not in ALLOWED_PORTS.values():
        raise UnsafeDestinationError("unsupported_port")
    host = canonical_host(parts.hostname)
    path = parts.path or "/"
    if parts.query:
        path += "?" + parts.query
    literal = _is_literal(host)
    return Target(scheme, host, port or ALLOWED_PORTS[scheme], path, literal)


def _is_literal(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return False
    return True


def canonical_host(raw: str | None) -> str:
    if not raw:
        raise UnsafeDestinationError("malformed_url")
    host = raw.rstrip(".").lower()
    if ":" in host:  # an IPv6 literal (urlsplit removes the brackets)
        try:
            return str(ipaddress.IPv6Address(host))
        except ValueError:
            raise UnsafeDestinationError("ambiguous_ip") from None
    if _NUMERICISH.match(host):
        # Digits, dots, and hex letters only: either a strict dotted quad or an ambiguous spelling.
        try:
            return str(ipaddress.IPv4Address(host))
        except ValueError:
            raise UnsafeDestinationError("ambiguous_ip") from None
    try:
        ascii_host = host.encode("idna").decode("ascii")
    except UnicodeError:
        raise UnsafeDestinationError("malformed_url") from None
    labels = ascii_host.split(".")
    if (
        len(ascii_host) > 253  # noqa: PLR2004
        or any(not _LABEL.match(label) for label in labels)
        or ascii_host == "localhost"
        or ascii_host.endswith(_BLOCKED_SUFFIXES)
        or "." not in ascii_host
        or labels[-1].isdigit()
    ):
        raise UnsafeDestinationError("blocked_host")
    return ascii_host


async def resolve_public(target: Target, resolver: Resolver) -> list[str]:
    """Addresses to connect to. Every resolved address must be public, or the host is refused."""
    if target.is_ip_literal:
        addresses = [target.host]
    else:
        addresses = await resolver.resolve(target.host)
    if not addresses:
        raise UnsafeDestinationError("dns_failure")
    if not all(is_public_address(a) for a in addresses):
        raise UnsafeDestinationError("private_address")
    return addresses
