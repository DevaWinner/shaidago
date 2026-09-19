"""Version 1 of the private HTTP API. Domain routers are included here by their owning tasks."""

from fastapi import APIRouter

router = APIRouter(prefix="/v1")
