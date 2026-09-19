"""Deterministic open/close of long-lived resources (connection pools, provider clients)."""

from collections.abc import AsyncGenerator, Sequence
from contextlib import AsyncExitStack, asynccontextmanager
from typing import Protocol


class ManagedResource(Protocol):
    """A resource opened once at startup and closed once at shutdown.

    ``open`` must release anything it acquired if it raises; ``close`` is only called after a
    successful ``open``.
    """

    async def open(self) -> None: ...

    async def close(self) -> None: ...


@asynccontextmanager
async def open_resources(resources: Sequence[ManagedResource]) -> AsyncGenerator[None]:
    """Open in order and close in reverse order, including when a later open or the body fails."""
    async with AsyncExitStack() as stack:
        for resource in resources:
            await resource.open()
            stack.push_async_callback(resource.close)
        yield
