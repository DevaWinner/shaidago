"""Worker process entry: ``dramatiq shaidago.worker.entry`` (module-level ``broker``).

Runtime wiring lives here and nowhere else: environment, engine, broker, and actors are created
once at process start, the way the API's ``create_configured_app`` does. The worker connects as
``shaidago_worker`` and never as the migration owner.
"""

import os
from typing import Final
from uuid import UUID

from shaidago.shared.clock import SystemClock
from shaidago.shared.config import load_settings
from shaidago.shared.database import Database, create_engine
from shaidago.shared.ids import Uuid7Generator
from shaidago.shared.logging import configure_logging
from shaidago.worker.broker import DiscoveryActors, build_redis_broker, register_actors
from shaidago.worker.pipeline import build_pipeline
from shaidago.worker.process import Outcome, fail_exhausted, process_run
from shaidago.worker.store import RunStore

CONFIG_VERSION: Final = "discovery-v1"


def create_worker() -> tuple[object, DiscoveryActors]:
    settings = load_settings(os.environ)
    configure_logging(
        service=f"{settings.app.service_name}-worker",
        environment=settings.app.environment,
        level=settings.observability.log_level,
    )
    database = Database(
        create_engine(
            settings.database,
            application_name=f"{settings.app.service_name}-worker",
            url=settings.database.worker_sqlalchemy_url(),
        )
    )
    clock = SystemClock()
    store = RunStore(database, clock, Uuid7Generator(clock))
    pipeline = build_pipeline(settings, store)

    async def handle(run_id: UUID, owner: str) -> Outcome:
        return await process_run(store, pipeline, run_id, owner)

    async def exhausted(run_id: UUID, code: str) -> None:
        await fail_exhausted(store, run_id, code)

    broker = build_redis_broker(settings.redis.url.get_secret_value())
    return broker, register_actors(broker, handle, exhausted)


broker, actors = create_worker()
