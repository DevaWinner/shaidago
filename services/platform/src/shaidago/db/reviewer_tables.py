"""Metadata for reviewer users and the append-only audit log (BE-050); checks are in 0007."""

from sqlalchemy import (
    Column,
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
)
from sqlalchemy.dialects.postgresql import JSONB

from shaidago.db.metadata import metadata

REVIEWER_ROLES = ("reviewer", "admin")
REVIEWER_STATES = ("active", "disabled")

reviewers = Table(
    "reviewers",
    metadata,
    Column("id", Uuid(), nullable=False),
    Column("identifier", Text(), nullable=False),
    Column("password_hash", Text(), nullable=False),
    Column("role", Text(), nullable=False),
    Column("state", Text(), nullable=False),
    Column("credential_version", Integer(), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("last_sign_in_at", DateTime(timezone=True)),
    PrimaryKeyConstraint("id"),
    UniqueConstraint("identifier"),
    schema="app",
)

audit_events = Table(
    "audit_events",
    metadata,
    Column("id", Uuid(), nullable=False),
    Column("occurred_at", DateTime(timezone=True), nullable=False),
    Column("actor_type", Text(), nullable=False),
    Column("actor_id", Uuid()),
    Column("event", Text(), nullable=False),
    Column("subject_type", Text()),
    Column("subject_id", Uuid()),
    Column("outcome", Text(), nullable=False),
    Column("request_id", Text()),
    Column("details", JSONB(), nullable=False),
    PrimaryKeyConstraint("id"),
    Index("ix_audit_events_occurred_at", "occurred_at"),
    Index("ix_audit_events_subject", "subject_type", "subject_id"),
    schema="app",
)

SESSION_REVOCATION_REASONS = (
    "logout",
    "disabled",
    "credential_change",
    "role_change",
    "admin_revoked",
    "expired",
)

reviewer_sessions = Table(
    "reviewer_sessions",
    metadata,
    Column("id", Uuid(), nullable=False),
    Column("token_hmac", LargeBinary(), nullable=False),
    Column(
        "reviewer_id", Uuid(), ForeignKey("app.reviewers.id", ondelete="RESTRICT"), nullable=False
    ),
    Column("role_snapshot", Text(), nullable=False),
    Column("credential_version", Integer(), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("last_used_at", DateTime(timezone=True), nullable=False),
    Column("absolute_expires_at", DateTime(timezone=True), nullable=False),
    Column("revoked_at", DateTime(timezone=True)),
    Column("revocation_reason", Text()),
    PrimaryKeyConstraint("id"),
    UniqueConstraint("token_hmac"),
    Index("ix_reviewer_sessions_reviewer_id", "reviewer_id"),
    schema="app",
)
