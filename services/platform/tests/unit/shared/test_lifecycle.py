import pytest

from shaidago.shared.lifecycle import open_resources


class Recorder:
    def __init__(self, name: str, log: list[str], *, fail_open: bool = False) -> None:
        self.name = name
        self.log = log
        self.fail_open = fail_open

    async def open(self) -> None:
        if self.fail_open:
            raise RuntimeError("open failed")
        self.log.append(f"open:{self.name}")

    async def close(self) -> None:
        self.log.append(f"close:{self.name}")


async def test_resources_open_in_order_and_close_in_reverse() -> None:
    log: list[str] = []
    async with open_resources([Recorder("db", log), Recorder("redis", log)]):
        log.append("running")
    assert log == ["open:db", "open:redis", "running", "close:redis", "close:db"]


async def test_failed_open_closes_only_what_was_opened() -> None:
    log: list[str] = []
    resources = [Recorder("db", log), Recorder("redis", log, fail_open=True), Recorder("s3", log)]
    with pytest.raises(RuntimeError, match="open failed"):
        async with open_resources(resources):
            pytest.fail("body must not run")
    assert log == ["open:db", "close:db"]


async def test_body_failure_still_closes_everything() -> None:
    log: list[str] = []
    with pytest.raises(ValueError, match="boom"):
        async with open_resources([Recorder("db", log)]):
            raise ValueError("boom")
    assert log == ["open:db", "close:db"]
