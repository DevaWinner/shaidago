"""Metadata for the private report tables (BE-061); checks and triggers are in 0010."""

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
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

from shaidago.db.metadata import metadata

REPORT_STATUSES = (
    "received",
    "needs_information",
    "under_review",
    "verified_for_public_update",
    "referred",
    "closed",
)
CONCERN_CATEGORIES = (
    "no_visible_work",
    "incomplete_work",
    "unsafe_construction",
    "suspected_incorrect_status",
    "access_barrier",
    "other_concern",
)


def _fk(target: str, action: str) -> ForeignKey:
    return ForeignKey(target, ondelete=action)


reports = Table(
    "reports",
    metadata,
    Column("id", Uuid(), nullable=False),
    Column("project_id", Uuid(), _fk("app.projects.id", "RESTRICT"), nullable=False),
    Column("concern_category", Text(), nullable=False),
    Column("description_ciphertext", LargeBinary(), nullable=False),
    Column("description_key_id", Uuid(), _fk("app.data_keys.id", "RESTRICT"), nullable=False),
    Column("schema_version", Integer(), nullable=False),
    Column("risk_level", Text(), nullable=False),
    Column("anonymous", Boolean(), nullable=False),
    Column("reporter_handle_id", Uuid(), _fk("app.reporter_handles.id", "SET NULL")),
    Column("status", Text(), nullable=False),
    Column("status_updated_at", DateTime(timezone=True), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    # Optimistic-concurrency token; a trigger raises it when status or risk level changes (0014).
    Column("version", Integer(), nullable=False, server_default=text("1")),
    PrimaryKeyConstraint("id"),
    Index("ix_reports_project_id", "project_id"),
    Index("ix_reports_status", "status", "created_at"),
    Index(
        "ix_reports_reporter_handle_id",
        "reporter_handle_id",
        postgresql_where=text("reporter_handle_id IS NOT NULL"),
    ),
    schema="app",
)

report_contacts = Table(
    "report_contacts",
    metadata,
    Column("id", Uuid(), nullable=False),
    Column("report_id", Uuid(), _fk("app.reports.id", "CASCADE"), nullable=False),
    Column("channel_ciphertext", LargeBinary()),
    Column("value_ciphertext", LargeBinary()),
    Column("data_key_id", Uuid(), _fk("app.data_keys.id", "RESTRICT"), nullable=False),
    Column("schema_version", Integer(), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("destroyed_at", DateTime(timezone=True)),
    PrimaryKeyConstraint("id"),
    UniqueConstraint("report_id"),
    schema="app",
)

report_status_events = Table(
    "report_status_events",
    metadata,
    Column("id", Uuid(), nullable=False),
    Column("report_id", Uuid(), _fk("app.reports.id", "CASCADE"), nullable=False),
    Column("previous_status", Text()),
    Column("new_status", Text(), nullable=False),
    Column("public_message", Text(), nullable=False),
    Column("actor_type", Text(), nullable=False),
    Column("actor_id", Uuid()),
    Column("occurred_at", DateTime(timezone=True), nullable=False),
    # Private encrypted reason for a reviewer decision (0015); tracking never reads these.
    Column("reason_ciphertext", LargeBinary()),
    Column("reason_key_id", Uuid(), _fk("app.data_keys.id", "RESTRICT")),
    Column("reason_schema_version", Integer()),
    PrimaryKeyConstraint("id"),
    Index("ix_report_status_events_report_id", "report_id", "occurred_at"),
    schema="app",
)

report_tracking_keys = Table(
    "report_tracking_keys",
    metadata,
    Column("id", Uuid(), nullable=False),
    Column("report_id", Uuid(), _fk("app.reports.id", "CASCADE"), nullable=False),
    Column("lookup_hmac", LargeBinary(), nullable=False),
    Column("pepper_version", Text(), nullable=False),
    Column("checksum_version", Integer(), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    PrimaryKeyConstraint("id"),
    UniqueConstraint("lookup_hmac"),
    UniqueConstraint("report_id"),
    schema="app",
)

evidence_files = Table(
    "evidence_files",
    metadata,
    Column("id", Uuid(), nullable=False),
    Column("report_id", Uuid(), _fk("app.reports.id", "CASCADE"), nullable=False),
    Column("object_key", Text(), nullable=False),
    Column("display_name", Text(), nullable=False),
    Column("sniffed_mime", Text(), nullable=False),
    Column("size_bytes", BigInteger(), nullable=False),
    Column("sha256", Text(), nullable=False),
    Column("sanitation_state", Text(), nullable=False),
    Column("scan_state", Text(), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    PrimaryKeyConstraint("id"),
    UniqueConstraint("object_key"),
    Index("ix_evidence_files_report_id", "report_id"),
    schema="app",
)


# Optional anonymous reporter handles (BE-066). No identity, contact, or recovery column exists.
reporter_handles = Table(
    "reporter_handles",
    metadata,
    Column("id", Uuid(), nullable=False),
    Column("handle", Text(), nullable=False),
    Column("passphrase_hash", Text(), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("last_used_on", Date()),
    Column("failure_count", Integer(), nullable=False, server_default=text("0")),
    Column("last_failure_at", DateTime(timezone=True)),
    Column("backoff_until", DateTime(timezone=True)),
    PrimaryKeyConstraint("id"),
    UniqueConstraint("handle", name="uq_reporter_handles_handle"),
    schema="app",
)


# Reviewer follow-up questions and private answers (BE-067); checks are in 0013.
report_follow_up_questions = Table(
    "report_follow_up_questions",
    metadata,
    Column("id", Uuid(), nullable=False),
    Column("report_id", Uuid(), _fk("app.reports.id", "CASCADE"), nullable=False),
    Column("question", Text(), nullable=False),
    Column("asked_by", Uuid(), _fk("app.reviewers.id", "SET NULL")),
    Column("asked_at", DateTime(timezone=True), nullable=False),
    Column("withdrawn_at", DateTime(timezone=True)),
    PrimaryKeyConstraint("id"),
    UniqueConstraint("id", "report_id", name="uq_report_follow_up_questions_id_report_id"),
    Index("ix_report_follow_up_questions_report_id", "report_id", "asked_at"),
    schema="app",
)

report_follow_up_answers = Table(
    "report_follow_up_answers",
    metadata,
    Column("id", Uuid(), nullable=False),
    Column("question_id", Uuid(), nullable=False),
    Column("report_id", Uuid(), nullable=False),
    Column("kind", Text(), nullable=False),
    Column("answer_ciphertext", LargeBinary()),
    Column("data_key_id", Uuid(), _fk("app.data_keys.id", "RESTRICT")),
    Column("schema_version", Integer(), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    PrimaryKeyConstraint("id"),
    UniqueConstraint("question_id", name="uq_report_follow_up_answers_question_id"),
    ForeignKeyConstraint(
        ["question_id", "report_id"],
        ["app.report_follow_up_questions.id", "app.report_follow_up_questions.report_id"],
        name="fk_report_follow_up_answers_question",
        ondelete="CASCADE",
    ),
    schema="app",
)


# Encrypted, append-only reviewer notes (BE-072); checks, policies, and the trigger are in 0016.
report_notes = Table(
    "report_notes",
    metadata,
    Column("id", Uuid(), nullable=False),
    Column("report_id", Uuid(), _fk("app.reports.id", "CASCADE"), nullable=False),
    Column("author_id", Uuid(), _fk("app.reviewers.id", "SET NULL")),
    Column("body_ciphertext", LargeBinary(), nullable=False),
    Column("data_key_id", Uuid(), _fk("app.data_keys.id", "RESTRICT"), nullable=False),
    Column("schema_version", Integer(), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    PrimaryKeyConstraint("id"),
    Index("ix_report_notes_report_id", "report_id", "created_at"),
    schema="app",
)
