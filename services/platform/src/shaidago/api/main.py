"""Process entry point: ``uvicorn --factory shaidago.api.main:create_configured_app``."""

import os

from fastapi import FastAPI
from redis.asyncio import Redis

from shaidago.api.app import create_app
from shaidago.api.dependencies import Dependencies
from shaidago.db.revision import MigrationRevisionCheck, expected_head
from shaidago.files.pipeline import EvidencePipeline, PipelineParts, SanitiserPool
from shaidago.files.rules import FileLimits
from shaidago.files.scanner import build_scanner
from shaidago.files.storage import S3ObjectStore
from shaidago.shared.config import load_settings
from shaidago.shared.database import Database, create_engine
from shaidago.shared.logging import configure_logging
from shaidago.shared.ratelimit import RedisRateLimiter


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
    reviewer = Database(
        create_engine(
            settings.database,
            application_name=settings.app.service_name,
            url=settings.database.reviewer_sqlalchemy_url(),
        )
    )
    limiter = RedisRateLimiter(
        Redis.from_url(  # pyright: ignore[reportUnknownMemberType]
            settings.redis.url.get_secret_value(), socket_connect_timeout=1, socket_timeout=1
        )
    )
    storage = settings.storage
    pool = SanitiserPool()
    limits = FileLimits()
    pipeline = EvidencePipeline(
        PipelineParts(
            build_scanner(
                storage.scanner_mode,
                app_env=settings.app.environment,
                host=storage.clamd_host,
                port=storage.clamd_port,
                timeout_seconds=limits.scan_timeout_seconds,
            ),
            S3ObjectStore(
                endpoint_url=storage.endpoint_url,
                bucket=storage.bucket,
                access_key_id=storage.access_key_id.get_secret_value(),
                secret_access_key=storage.secret_access_key.get_secret_value(),
                timeout_seconds=limits.store_timeout_seconds,
            ),
            pool.executor,
        ),
        limits=limits,
    )
    revision_check = MigrationRevisionCheck(public, expected_head())
    return create_app(
        settings,
        Dependencies(
            resources=(public, reviewer, limiter, pool),
            health_checks=(public, revision_check),
            public_database=public,
            reviewer_database=reviewer,
            rate_limiter=limiter,
            evidence_pipeline=pipeline,
        ),
    )
