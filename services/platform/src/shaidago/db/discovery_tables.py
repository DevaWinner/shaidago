"""Metadata for Source Scout discovery runs (BE-090); checks and the guard trigger are in 0021."""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    PrimaryKeyConstraint,
    Table,
    Text,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB

from shaidago.db.metadata import metadata

DISCOVERY_STATUSES = (
    "queued",
    "searching",
    "analysing",
    "needs_review",
    "complete",
    "failed",
    "cancelled",
)

discovery_runs = Table(
    "discovery_runs",
    metadata,
    Column("id", Uuid(), nullable=False),
    Column("scope", Text(), nullable=False),
    Column(
        "project_id", Uuid(), ForeignKey("app.projects.id", ondelete="RESTRICT"), nullable=False
    ),
    Column("report_id", Uuid(), ForeignKey("app.reports.id", ondelete="CASCADE")),
    Column("requested_by", Uuid(), ForeignKey("app.reviewers.id", ondelete="SET NULL")),
    Column("status", Text(), nullable=False),
    Column("attempts", Integer(), nullable=False, server_default=text("0")),
    Column("lease_owner", Text()),
    Column("lease_expires_at", DateTime(timezone=True)),
    Column("cancel_requested", Boolean(), nullable=False, server_default=text("false")),
    Column("failure_code", Text()),
    Column("query_text", Text()),
    Column("query_policy_version", Text()),
    Column("query_approved_by", Uuid(), ForeignKey("app.reviewers.id", ondelete="SET NULL")),
    Column("provider_mode", Text(), nullable=False),
    Column("demo_replay", Boolean(), nullable=False, server_default=text("false")),
    Column("model_id", Text()),
    Column("prompt_version", Text()),
    Column("results_found", Integer(), nullable=False, server_default=text("0")),
    Column("fetched_count", Integer(), nullable=False, server_default=text("0")),
    Column("analysed_count", Integer(), nullable=False, server_default=text("0")),
    Column("version", Integer(), nullable=False, server_default=text("1")),
    Column("analysis", JSONB()),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("started_at", DateTime(timezone=True)),
    Column("finished_at", DateTime(timezone=True)),
    PrimaryKeyConstraint("id"),
    Index("ix_discovery_runs_project_id", "project_id", "created_at"),
    Index(
        "ix_discovery_runs_report_id", "report_id", postgresql_where=text("report_id IS NOT NULL")
    ),
    Index(
        "ix_discovery_runs_active",
        "status",
        postgresql_where=text("status IN ('queued', 'searching', 'analysing')"),
    ),
    schema="app",
)
