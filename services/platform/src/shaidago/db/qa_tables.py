"""Operational metadata for grounded project questions; raw question text is never stored."""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    PrimaryKeyConstraint,
    Table,
    Text,
    Uuid,
)

from shaidago.db.metadata import metadata

question_runs = Table(
    "question_runs",
    metadata,
    Column("id", Uuid(), nullable=False),
    Column(
        "project_id", Uuid(), ForeignKey("app.projects.id", ondelete="RESTRICT"), nullable=False
    ),
    Column("request_id", Text(), nullable=False),
    Column("requested_locale", Text(), nullable=False),
    Column("served_locale", Text()),
    Column("retrieval_mode", Text(), nullable=False),
    Column("retrieved_chunks", Integer(), nullable=False),
    Column("cited_sources", Integer(), nullable=False),
    Column("outcome", Text(), nullable=False),
    Column("model_id", Text(), nullable=False),
    Column("prompt_version", Text(), nullable=False),
    Column("schema_version", Text(), nullable=False),
    Column("demo_replay", Boolean()),
    Column("failure_code", Text()),
    Column("validation_findings", Integer(), nullable=False),
    Column("duration_ms", Integer(), nullable=False),
    Column("started_at", DateTime(timezone=True), nullable=False),
    Column("completed_at", DateTime(timezone=True), nullable=False),
    PrimaryKeyConstraint("id"),
    CheckConstraint("char_length(request_id) BETWEEN 1 AND 64", name="request_id"),
    CheckConstraint("requested_locale IN ('en', 'ha', 'ig', 'yo')", name="requested_locale"),
    CheckConstraint(
        "served_locale IS NULL OR served_locale IN ('en', 'ha', 'ig', 'yo')",
        name="served_locale",
    ),
    CheckConstraint("retrieval_mode IN ('keyword', 'hybrid')", name="retrieval_mode"),
    CheckConstraint("retrieved_chunks BETWEEN 0 AND 5", name="retrieved_chunks"),
    CheckConstraint("cited_sources BETWEEN 0 AND 5", name="cited_sources"),
    CheckConstraint("outcome IN ('answered', 'fallback', 'provider_unavailable')", name="outcome"),
    CheckConstraint("char_length(model_id) BETWEEN 1 AND 100", name="model_id"),
    CheckConstraint("char_length(prompt_version) BETWEEN 1 AND 100", name="prompt_version"),
    CheckConstraint("char_length(schema_version) BETWEEN 1 AND 100", name="schema_version"),
    CheckConstraint(
        "failure_code IS NULL OR failure_code ~ '^[a-z][a-z0-9_]{0,99}$'", name="failure_code"
    ),
    CheckConstraint("validation_findings BETWEEN 0 AND 100", name="validation_findings"),
    CheckConstraint("duration_ms BETWEEN 0 AND 120000", name="duration_ms"),
    CheckConstraint("completed_at >= started_at", name="timestamps"),
    Index("ix_question_runs_project_started", "project_id", "started_at"),
    Index("ix_question_runs_outcome_started", "outcome", "started_at"),
    schema="app",
)
