"""Metadata for sources, immutable source versions, facts, updates, and their citations (BE-041).

Value lists are literal copies of ``contracts/controlled-vocabulary.json`` (checked by
``tests/unit/sources/test_vocabulary_parity.py``). Check constraints and triggers live in
revision 0004; this metadata lets autogenerate compare columns, keys, and indexes.
"""

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    PrimaryKeyConstraint,
    Table,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.schema import SchemaItem

from shaidago.db.metadata import metadata

SOURCE_TYPES = (
    "government_publication",
    "budget_document",
    "procurement_record",
    "audit_oversight_report",
    "independent_media",
    "civic_research",
    "community_evidence",
    "other_public_source",
)
PUBLIC_INFORMATION_CLASSES = (
    "official_source",
    "independent_source",
    "community_evidence_reviewed",
)
SOURCE_AVAILABILITIES = (
    "unchecked",
    "available",
    "temporarily_unavailable",
    "access_restricted",
    "permanently_unavailable",
)
SOURCE_REVIEW_STATES = ("pending", "in_review", "approved", "rejected", "superseded")
CITABLE_REVIEW_STATES = ("approved", "superseded")
VERIFICATION_STATES = (
    "awaiting_verification",
    "verified_official",
    "corroborated",
    "community_reviewed",
    "disputed",
    "outdated",
)
PUBLICATION_STATES = ("draft", "public")
MAX_PASSAGE_CHARS = 1000

sources = Table(
    "sources",
    metadata,
    Column("id", Uuid(), nullable=False),
    Column("canonical_url", Text(), nullable=False),
    Column("title", Text(), nullable=False),
    Column("publisher", Text(), nullable=False),
    Column("source_type", Text(), nullable=False),
    Column("information_class", Text(), nullable=False),
    Column("availability", Text(), nullable=False),
    Column("availability_checked_at", DateTime(timezone=True)),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    PrimaryKeyConstraint("id"),
    UniqueConstraint("canonical_url"),
    schema="app",
)

source_versions = Table(
    "source_versions",
    metadata,
    Column("id", Uuid(), nullable=False),
    Column("source_id", Uuid(), ForeignKey("app.sources.id", ondelete="RESTRICT"), nullable=False),
    Column("content_sha256", Text(), nullable=False),
    Column("content_text", Text(), nullable=False),
    Column("media_type", Text(), nullable=False),
    Column("retrieved_at", DateTime(timezone=True), nullable=False),
    Column("review_state", Text(), nullable=False),
    Column("reviewed_at", DateTime(timezone=True)),
    Column("reviewer_note", Text()),
    Column("created_at", DateTime(timezone=True), nullable=False),
    PrimaryKeyConstraint("id"),
    UniqueConstraint("source_id", "content_sha256"),
    Index("ix_source_versions_source_id", "source_id"),
    schema="app",
)


def _claim_table(name: str, *, kind: bool) -> Table:
    columns: list[SchemaItem] = [
        Column("id", Uuid(), nullable=False),
        Column(
            "project_id",
            Uuid(),
            ForeignKey("app.projects.id", ondelete="RESTRICT"),
            nullable=False,
        ),
    ]
    if kind:
        columns.append(Column("kind", Text(), nullable=False))
    columns += [
        Column("statement", Text(), nullable=False),
        Column("effective_on", Date()),
        Column("last_checked_on", Date()),
        Column("verification_state", Text(), nullable=False),
        Column("visibility", Text(), nullable=False),
        Column("published_at", DateTime(timezone=True)),
        Column("created_at", DateTime(timezone=True), nullable=False),
        Column("updated_at", DateTime(timezone=True), nullable=False),
        PrimaryKeyConstraint("id"),
        Index(f"ix_{name}_project_id", "project_id"),
    ]
    return Table(name, metadata, *columns, schema="app")


project_facts = _claim_table("project_facts", kind=True)
project_updates = _claim_table("project_updates", kind=False)


def _citation_table(name: str, parent: str, parent_column: str) -> Table:
    return Table(
        name,
        metadata,
        Column("id", Uuid(), nullable=False),
        Column(
            parent_column,
            Uuid(),
            ForeignKey(f"app.{parent}.id", ondelete="CASCADE"),
            nullable=False,
        ),
        Column(
            "source_version_id",
            Uuid(),
            ForeignKey("app.source_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        Column("passage", Text(), nullable=False),
        Column("location_label", Text(), nullable=False),
        Column("passage_start", Integer(), nullable=False),
        Column("created_at", DateTime(timezone=True), nullable=False),
        PrimaryKeyConstraint("id"),
        UniqueConstraint(parent_column, "source_version_id", "location_label"),
        Index(f"ix_{name}_source_version_id", "source_version_id"),
        schema="app",
    )


fact_citations = _citation_table("fact_citations", "project_facts", "fact_id")
update_citations = _citation_table("update_citations", "project_updates", "update_id")


# Reviewer-authored public updates and their citations (BE-074). The private link to the report
# lives only here; checks, policies, the guard trigger, and the publish function are in 0017.
public_updates = Table(
    "public_updates",
    metadata,
    Column("id", Uuid(), nullable=False),
    Column("report_id", Uuid(), ForeignKey("app.reports.id", ondelete="RESTRICT"), nullable=False),
    Column(
        "project_id", Uuid(), ForeignKey("app.projects.id", ondelete="RESTRICT"), nullable=False
    ),
    Column("statement", Text(), nullable=False),
    Column("effective_on", Date(), nullable=False),
    Column("last_checked_on", Date()),
    Column("verification_state", Text(), nullable=False),
    Column("state", Text(), nullable=False),
    Column("authored_by", Uuid(), ForeignKey("app.reviewers.id", ondelete="SET NULL")),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("published_by", Uuid(), ForeignKey("app.reviewers.id", ondelete="SET NULL")),
    Column("published_at", DateTime(timezone=True)),
    PrimaryKeyConstraint("id"),
    Index("ix_public_updates_report_id", "report_id"),
    schema="app",
)

public_update_citations = Table(
    "public_update_citations",
    metadata,
    Column("id", Uuid(), nullable=False),
    Column(
        "public_update_id",
        Uuid(),
        ForeignKey("app.public_updates.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "source_version_id",
        Uuid(),
        ForeignKey("app.source_versions.id", ondelete="RESTRICT"),
        nullable=False,
    ),
    Column("passage", Text(), nullable=False),
    Column("location_label", Text(), nullable=False),
    Column("passage_start", Integer(), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    PrimaryKeyConstraint("id"),
    UniqueConstraint(
        "public_update_id",
        "source_version_id",
        "location_label",
        name="uq_public_update_citations_update_version_label",
    ),
    Index("ix_public_update_citations_source_version_id", "source_version_id"),
    schema="app",
)
