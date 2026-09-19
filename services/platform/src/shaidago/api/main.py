"""Process entry point: ``uvicorn --factory shaidago.api.main:create_configured_app``."""

import os

from fastapi import FastAPI

from shaidago.api.app import create_app
from shaidago.api.dependencies import Dependencies
from shaidago.db.revision import MigrationRevisionCheck, expected_head
from shaidago.shared.config import load_settings
from shaidago.shared.database import Database, create_engine
from shaidago.shared.logging import configure_logging


def create_configured_app() -> FastAPI:
    settings = load_settings(os.environ)
    configure_logging(
        service=settings.app.service_name,
        environment=settings.app.environment,
        level=settings.observability.log_level,
    )
    # The running API never uses the migration owner: public reads go through shaidago_public.
    public = Database(
        create_engine(
            settings.database,
            application_name=settings.app.service_name,
            url=settings.database.public_sqlalchemy_url(),
        )
    )
    revision_check = MigrationRevisionCheck(public, expected_head())
    return create_app(
        settings,
        Dependencies(
            resources=(public,), health_checks=(public, revision_check), public_database=public
        ),
    )
