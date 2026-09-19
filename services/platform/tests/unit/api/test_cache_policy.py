"""The cache middleware: public reads keep their headers; everything else is no-store."""

import httpx
import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from shaidago.api.cache_policy import (
    PUBLIC_CACHEABLE_PATHS,
    CachePolicyMiddleware,
    may_be_publicly_cached,
)

PUBLIC = "public, max-age=60"


async def declared(request: Request) -> Response:
    status = int(request.query_params.get("status", "200"))
    header = request.query_params.get("cache", PUBLIC)
    return JSONResponse(
        {"ok": True},
        status_code=status,
        headers={"Cache-Control": header, "Pragma": "cache", "Expires": "never"},
    )


async def silent(_request: Request) -> Response:
    return JSONResponse({"ok": True})


def client() -> httpx.AsyncClient:
    app = Starlette(
        routes=[
            Route("/v1/projects", declared),
            Route("/v1/projects/{slug}", declared),
            Route("/v1/localities", declared),
            Route("/v1/reports", declared, methods=["GET", "POST"]),
            Route("/v1/reviewer/reports", silent),
            Route("/v1/projects/{slug}/sources/{sid}", declared),
        ]
    )
    app.add_middleware(CachePolicyMiddleware)
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def test_a_public_read_keeps_the_route_s_cache_header() -> None:
    async with client() as http:
        for path in (
            "/v1/projects",
            "/v1/projects/clinic",
            "/v1/localities",
            "/v1/projects/clinic/sources/" + "a" * 36,
        ):
            response = await http.get(path)
            assert response.headers["cache-control"] == PUBLIC, path
        assert (await http.get("/v1/projects", params={"status": "304"})).headers[
            "cache-control"
        ] == PUBLIC


async def test_a_public_header_on_any_other_response_is_replaced() -> None:
    async with client() as http:
        for response in (
            await http.get("/v1/reports"),
            await http.post("/v1/reports"),
            await http.get("/v1/projects", params={"status": "404"}),
            await http.get("/v1/projects", params={"status": "500"}),
            await http.get("/v1/projects/a/b"),
        ):
            assert response.headers["cache-control"] == "no-store"
            assert "pragma" not in response.headers
            assert "expires" not in response.headers


async def test_a_route_that_says_nothing_is_no_store_and_a_weaker_public_header_cannot_leak() -> (
    None
):
    async with client() as http:
        assert (await http.get("/v1/reviewer/reports")).headers["cache-control"] == "no-store"
        assert (await http.get("/v1/projects", params={"cache": "no-cache"})).headers[
            "cache-control"
        ] == "no-cache"
        assert (await http.post("/v1/projects")).status_code == 405
        assert (await http.post("/v1/projects")).headers["cache-control"] == "no-store"


@pytest.mark.parametrize(
    ("method", "path", "status", "expected"),
    [
        ("GET", "/v1/projects", 200, True),
        ("GET", "/v1/projects/clinic", 304, True),
        ("GET", "/v1/projects/clinic", 404, False),
        ("HEAD", "/v1/projects", 200, False),
        ("POST", "/v1/projects", 200, False),
        ("GET", "/v1/projects/clinic/questions", 200, False),
        ("GET", "/v1/projects/Clinic", 200, False),
        ("GET", "/v1/discovery-runs/" + "a" * 36, 200, False),
        ("GET", "/v1/reviewer/reports", 200, False),
        ("GET", "/health/ready", 200, False),
        ("GET", "/v1/projects/", 200, False),
    ],
)
def test_only_the_four_public_reads_may_be_cached(
    method: str, path: str, status: int, expected: bool
) -> None:
    assert may_be_publicly_cached(method, path, status) is expected
    assert len(PUBLIC_CACHEABLE_PATHS) == 4
