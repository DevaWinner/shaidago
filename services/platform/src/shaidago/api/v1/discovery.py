"""Public Source Scout: start or re-use one shared run per project, and read its scope-safe result.

Runs are shared and cost-bounded, so anonymous callers can neither cancel nor steer them. A public
run id never resolves a report-scoped run (the read model is a view over public runs only), and
every result carries the label ``discovered — not yet reviewed``: nothing found here is attached,
verified, or published.
"""

from datetime import date, datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from pydantic import BaseModel

from shaidago.api.dependencies import Dependencies, get_dependencies, get_settings
from shaidago.api.rate_limits import enforce_rate_limit
from shaidago.api.v1.projects import public_database, reject_unknown_query
from shaidago.discovery import service
from shaidago.discovery.analysis import LABEL
from shaidago.shared.config import Settings
from shaidago.shared.database import Database
from shaidago.shared.problems import DEPENDENCY_UNAVAILABLE, NOT_FOUND, ProblemDetails, ProblemError

router = APIRouter(tags=["discovery"])
PROBLEMS: dict[int | str, dict[str, Any]] = {
    404: {"model": ProblemDetails},
    422: {"model": ProblemDetails},
    429: {"model": ProblemDetails},
    503: {"model": ProblemDetails},
}
Action = Literal["create", "reuse_fresh", "show_latest_completed", "unavailable"]


class ProgressOut(BaseModel):
    results_found: int
    fetched: int
    analysed: int


class RunStartedOut(BaseModel):
    run_id: UUID | None
    action: Action
    status: str | None
    demo_replay: bool | None
    label: str = LABEL


class SourceCardOut(BaseModel):
    source_id: UUID
    canonical_url: str
    publisher_domain: str
    title: str | None
    preliminary_type: str
    published_on: date | None
    published_provenance: str
    date_conflict: bool
    excerpt: str
    availability: str
    first_discovered_at: datetime
    last_retrieved_at: datetime
    label: str = LABEL


class RunOut(BaseModel):
    run_id: UUID
    project_slug: str
    status: str
    version: int
    progress: ProgressOut
    demo_replay: bool
    created_at: datetime
    finished_at: datetime | None
    failure_code: str | None
    label: str = LABEL
    sources: list[SourceCardOut]
    result: dict[str, Any] | None


def _queue(dependencies: Dependencies) -> Any:
    if dependencies.job_queue is None:
        raise ProblemError(DEPENDENCY_UNAVAILABLE)
    return dependencies.job_queue


@router.post("/projects/{slug}/discovery-runs", response_model=RunStartedOut, responses=PROBLEMS)
async def start_public_run(  # noqa: PLR0913 - a route names its collaborators
    slug: str,
    *,
    request: Request,
    response: Response,
    database: Annotated[Database, Depends(public_database)],
    dependencies: Annotated[Dependencies, Depends(get_dependencies)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> RunStartedOut:
    response.headers["Cache-Control"] = "no-store"
    queue = _queue(dependencies)
    client = getattr(request.state, "client_hmac", None) or "unknown"
    await enforce_rate_limit(
        dependencies, f"sg:rl:discovery:{client}", limit=settings.rate_limits.discovery_per_hour
    )
    async with database.unit_of_work() as session:
        started = await service.request_public_run(
            session,
            dependencies.clock,
            dependencies.ids,
            slug,
            daily_limit=settings.rate_limits.discovery_public_daily_runs,
            provider_mode=settings.providers.mode,
        )
        if started is None:
            raise ProblemError(NOT_FOUND)
        shown = None
        if started.action != "unavailable":
            shown = await service.public_run_view(session, started.run_id)
    if started.enqueue:
        await queue.enqueue_discovery(started.run_id)  # the job carries the run ID only
    run = shown[0] if shown else None
    return RunStartedOut(
        run_id=None if started.action == "unavailable" else started.run_id,
        action=started.action,  # type: ignore[arg-type]
        status=None if run is None else run.status,
        demo_replay=None if run is None else run.demo_replay,
    )


@router.get("/discovery-runs/{run_id}", response_model=RunOut, responses=PROBLEMS)
async def get_public_run(
    run_id: UUID,
    request: Request,
    response: Response,
    database: Annotated[Database, Depends(public_database)],
    since_version: Annotated[int | None, Query(ge=0, le=1_000_000)] = None,
) -> Response | RunOut:
    reject_unknown_query(request, frozenset({"since_version"}))
    async with database.unit_of_work() as session:
        found = await service.public_run_view(session, run_id)
    if found is None:
        raise ProblemError(NOT_FOUND)
    run, sources = found
    headers = {"Cache-Control": "no-store"}
    if since_version is not None and since_version == run.version:
        return Response(status_code=304, headers=headers)  # nothing changed since the last poll
    response.headers.update(headers)
    return RunOut(
        run_id=run.id,
        project_slug=run.project_slug,
        status=run.status,
        version=run.version,
        progress=ProgressOut(
            results_found=run.results_found, fetched=run.fetched_count, analysed=run.analysed_count
        ),
        demo_replay=run.demo_replay,
        created_at=run.created_at,
        finished_at=run.finished_at,
        failure_code=run.failure_code,
        sources=[SourceCardOut.model_validate(dict(s._mapping)) for s in sources],
        result=run.analysis if run.status == "complete" else None,
    )
