"""Metadata for Source Scout discovery runs (BE-090); checks and the guard trigger are in 0021."""

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    PrimaryKeyConstraint,
    Table,
    Text,
    UniqueConstraint,
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

discovered_sources = Table(
    "discovered_sources",
    metadata,
    Column("id", Uuid(), nullable=False),
    Column("scope", Text(), nullable=False),
    Column(
        "project_id", Uuid(), ForeignKey("app.projects.id", ondelete="RESTRICT"), nullable=False
    ),
    Column("report_id", Uuid(), ForeignKey("app.reports.id", ondelete="CASCADE")),
    Column("canonical_url", Text(), nullable=False),
    Column("publisher_domain", Text(), nullable=False),
    Column("title", Text()),
    Column("preliminary_type", Text(), nullable=False),
    Column("published_on", Date()),
    Column("published_provenance", Text(), nullable=False),
    Column("date_conflict", Boolean(), nullable=False),
    Column("content_type", Text(), nullable=False),
    Column("excerpt", Text(), nullable=False),
    Column("text_sha256", Text(), nullable=False),
    Column("simhash", BigInteger(), nullable=False),
    Column("extraction_version", Text(), nullable=False),
    Column("injection_flag", Boolean(), nullable=False),
    Column("duplicate_of", Uuid(), ForeignKey("app.discovered_sources.id", ondelete="SET NULL")),
    Column("duplicate_kind", Text()),
    Column("availability", Text(), nullable=False),
    Column("disposition", Text(), nullable=False, server_default=text("'not_reviewed'")),
    Column("first_discovered_at", DateTime(timezone=True), nullable=False),
    Column("last_retrieved_at", DateTime(timezone=True), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    # Reviewer decision (0023): attaching creates a pending source, never an approved one.
    Column("attached_source_id", Uuid(), ForeignKey("app.sources.id", ondelete="SET NULL")),
    Column("decided_by", Uuid(), ForeignKey("app.reviewers.id", ondelete="SET NULL")),
    Column("decided_at", DateTime(timezone=True)),
    Column("decision_reason_ciphertext", LargeBinary()),
    Column("decision_key_id", Uuid(), ForeignKey("app.data_keys.id", ondelete="RESTRICT")),
    PrimaryKeyConstraint("id"),
    Index(
        "uq_discovered_sources_scope_url",
        "scope",
        text("COALESCE(report_id, project_id)"),
        "canonical_url",
        unique=True,
    ),
    Index(
        "ix_discovered_sources_hash",
        "scope",
        text("COALESCE(report_id, project_id)"),
        "text_sha256",
    ),
    schema="app",
)

discovered_source_sightings = Table(
    "discovered_source_sightings",
    metadata,
    Column("id", Uuid(), nullable=False),
    Column(
        "discovered_source_id",
        Uuid(),
        ForeignKey("app.discovered_sources.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "run_id", Uuid(), ForeignKey("app.discovery_runs.id", ondelete="CASCADE"), nullable=False
    ),
    Column("discovered_at", DateTime(timezone=True), nullable=False),
    Column("retrieved_at", DateTime(timezone=True), nullable=False),
    PrimaryKeyConstraint("id"),
    UniqueConstraint(
        "discovered_source_id", "run_id", name="uq_discovered_source_sightings_source_run"
    ),
    Index("ix_discovered_source_sightings_run_id", "run_id"),
    schema="app",
)

discovery_follow_up_answers = Table(
    "discovery_follow_up_answers",
    metadata,
    Column("id", Uuid(), nullable=False),
    Column(
        "run_id", Uuid(), ForeignKey("app.discovery_runs.id", ondelete="CASCADE"), nullable=False
    ),
    Column("question_index", Integer(), nullable=False),
    Column("kind", Text(), nullable=False),
    Column("answer_ciphertext", LargeBinary()),
    Column("data_key_id", Uuid(), ForeignKey("app.data_keys.id", ondelete="RESTRICT")),
    Column("schema_version", Integer(), nullable=False),
    Column("answered_by", Uuid(), ForeignKey("app.reviewers.id", ondelete="SET NULL")),
    Column("created_at", DateTime(timezone=True), nullable=False),
    PrimaryKeyConstraint("id"),
    UniqueConstraint(
        "run_id", "question_index", name="uq_discovery_follow_up_answers_run_question"
    ),
    schema="app",
)
