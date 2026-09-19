"""Container entry point: ``python -m shaidago.api.serve``.

Binds one dual-stack socket on ``::`` (IPv6 for Railway's private network) with ``IPV6_V6ONLY``
explicitly off, so IPv4 also works whatever the host's ``bindv6only`` setting is (a bare
``--host ::`` is IPv6-only on some hosts and container runtimes). The socket is handed to uvicorn,
which drains in-flight requests on SIGTERM within the graceful-shutdown timeout.
"""

import os
import socket
import sys

import uvicorn

GRACEFUL_SHUTDOWN_SECONDS = 25


def dual_stack_socket(port: int) -> socket.socket:
    return socket.create_server(
        ("::", port), family=socket.AF_INET6, dualstack_ipv6=True, backlog=128
    )


def main() -> None:
    port = int(os.environ.get("PORT", "8000"))
    server_socket = dual_stack_socket(port)
    config = uvicorn.Config(
        "shaidago.api.main:create_configured_app",
        factory=True,
        fd=server_socket.fileno(),
        timeout_graceful_shutdown=GRACEFUL_SHUTDOWN_SECONDS,
        server_header=False,
        access_log=False,  # the request log middleware writes one redacted line per request
        log_config=None,
    )
    uvicorn.Server(config).run()
    server_socket.close()


if __name__ == "__main__":
    sys.exit(main())
