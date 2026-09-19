"""Version 1 of the private HTTP API. Domain routers are included here by their owning tasks."""

from fastapi import APIRouter

from shaidago.api.v1 import projects

router = APIRouter(prefix="/v1")
router.include_router(projects.localities_router)
router.include_router(projects.router)
