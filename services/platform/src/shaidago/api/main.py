"""Process entry point: ``uvicorn --factory shaidago.api.main:create_configured_app``."""

import os

from fastapi import FastAPI

from shaidago.api.app import create_app
from shaidago.api.dependencies import Dependencies
from shaidago.shared.config import load_settings


def create_configured_app() -> FastAPI:
    return create_app(load_settings(os.environ), Dependencies())
