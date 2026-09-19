"""Process entry point: ``uvicorn --factory shaidago.api.main:create_configured_app``."""

import os

from fastapi import FastAPI
from redis.asyncio import Redis

from shaidago.api.app import create_app
from shaidago.api.dependencies import Dependencies
from shaidago.db.revision import MigrationRevisionCheck, expected_head
from shaidago.files.pipeline import EvidencePipeline, PipelineParts, SanitiserPool
from shaidago.files.rules import FileLimits
from shaidago.files.scanner import ClamdScanner, build_scanner
from shaidago.files.storage import S3ObjectStore
from shaidago.retrieval.groq import GroqLanguageModel
from shaidago.retrieval.language import QA_FIXTURES_ROOT, FixtureLanguageModel
from shaidago.shared.config import load_settings
from shaidago.shared.database import Database, create_engine
from shaidago.shared.health import HealthCheck
from shaidago.shared.logging import configure_logging
from shaidago.shared.probes import CallableProbe
from shaidago.shared.ratelimit import RedisRateLimiter
from shaidago.worker.queue import build_producer_queue


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
    redis = Redis.from_url(  # pyright: ignore[reportUnknownMemberType]
        settings.redis.url.get_secret_value(), socket_connect_timeout=1, socket_timeout=1
    )
    limiter = RedisRateLimiter(redis)
    storage = settings.storage
    pool = SanitiserPool()
    limits = FileLimits()
    revision_check = MigrationRevisionCheck(public, expected_head())
    scanner = build_scanner(
        storage.scanner_mode,
        app_env=settings.app.environment,
        host=storage.clamd_host,
        port=storage.clamd_port,
        timeout_seconds=limits.scan_timeout_seconds,
    )
    store = S3ObjectStore(
        endpoint_url=storage.endpoint_url,
        bucket=storage.bucket,
        access_key_id=storage.access_key_id.get_secret_value(),
        secret_access_key=storage.secret_access_key.get_secret_value(),
        timeout_seconds=limits.store_timeout_seconds,
    )
    pipeline = EvidencePipeline(PipelineParts(scanner, store, pool.executor), limits=limits)
    language_model: FixtureLanguageModel | GroqLanguageModel
    managed_providers: tuple[GroqLanguageModel, ...] = ()
    if settings.providers.mode == "replay":
        language_model = FixtureLanguageModel.from_path(QA_FIXTURES_ROOT / "grounded-qa-v1.json")
    else:
        key = settings.providers.language_api_key
        if key is None:  # load_settings enforces this; keep the construction boundary explicit.
            raise RuntimeError("live Q&A provider is not configured")
        language_model = GroqLanguageModel(
            api_key=key.get_secret_value(),
            model_id=settings.providers.qa_model,
            base_url=settings.providers.language_base_url,
        )
        managed_providers = (language_model,)
    probes: list[HealthCheck] = [
        public,
        revision_check,
        CallableProbe("redis", limiter.check, required=True),
        CallableProbe("object_storage", store.check, required=True),
    ]
    if isinstance(scanner, ClamdScanner):  # the hosted demo runs without a scanner
        probes.append(CallableProbe("scanner", scanner.ping, required=True))
    return create_app(
        settings,
        Dependencies(
            resources=(public, reviewer, limiter, pool, *managed_providers),
            health_checks=tuple(probes),
            public_database=public,
            reviewer_database=reviewer,
            rate_limiter=limiter,
            language_model=language_model,
            evidence_pipeline=pipeline,
            evidence_store=store,
            job_queue=build_producer_queue(settings.redis.url.get_secret_value()),
        ),
    )
