"""Readiness probes for infrastructure clients, wrapping one cheap call each."""

from collections.abc import Awaitable, Callable


class CallableProbe:
    """A dependency check that passes when ``call`` returns and fails when it raises."""

    def __init__(self, name: str, call: Callable[[], Awaitable[object]], *, required: bool) -> None:
        self.name = name
        self.required = required
        self._call = call

    async def check(self) -> None:
        await self._call()
