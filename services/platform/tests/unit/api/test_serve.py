"""The container entry point binds one socket that answers over both IP families."""

import socket

import pytest

from shaidago.api.serve import dual_stack_socket


def has_ipv6() -> bool:
    try:
        probe = socket.socket(socket.AF_INET6)
        probe.bind(("::1", 0))
        probe.close()
    except OSError:
        return False
    return True


@pytest.mark.skipif(not has_ipv6(), reason="this host has no IPv6 loopback")
def test_the_socket_accepts_ipv4_and_ipv6_clients() -> None:
    server = dual_stack_socket(0)
    port = server.getsockname()[1]
    try:
        for family, address in ((socket.AF_INET, "127.0.0.1"), (socket.AF_INET6, "::1")):
            with socket.socket(family) as client:
                client.settimeout(2)
                client.connect((address, port))
                accepted, _ = server.accept()
                accepted.close()
    finally:
        server.close()
