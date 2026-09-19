"""Version 1 of the private HTTP API. Domain routers are included here by their owning tasks."""

from fastapi import APIRouter

from shaidago.api.v1 import (
    auth,
    follow_ups,
    projects,
    report_status,
    reporter_handles,
    reports,
    reviewer_decisions,
    reviewer_evidence,
    reviewer_notes,
    reviewer_publication,
    reviewer_reports,
)

router = APIRouter(prefix="/v1")
router.include_router(auth.router)
router.include_router(projects.localities_router)
router.include_router(projects.router)
router.include_router(reports.router)
router.include_router(report_status.router)
router.include_router(follow_ups.router)
router.include_router(reporter_handles.router)
router.include_router(reviewer_reports.router)
router.include_router(reviewer_decisions.router)
router.include_router(reviewer_notes.router)
router.include_router(reviewer_evidence.router)
router.include_router(reviewer_publication.router)
