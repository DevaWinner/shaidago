"""Metadata for escalation routes (BE-042). Constraints and the trigger live in revision 0005."""

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    PrimaryKeyConstraint,
    Table,
    Text,
    UniqueConstraint,
    Uuid,
)

from shaidago.db.metadata import metadata

CONCERN_CATEGORIES = (
    "no_visible_work",
    "incomplete_work",
    "unsafe_construction",
    "suspected_incorrect_status",
    "access_barrier",
    "other_concern",
)

escalation_routes = Table(
    "escalation_routes",
    metadata,
    Column("id", Uuid(), nullable=False),
    Column(
        "locality_id",
        Uuid(),
        ForeignKey("app.localities.id", ondelete="RESTRICT"),
        nullable=False,
    ),
    Column("concern_category", Text()),
    Column("locale", Text(), nullable=False),
    Column("organisation", Text(), nullable=False),
    Column("instructions", Text(), nullable=False),
    Column("disclaimer", Text(), nullable=False),
    Column(
        "source_version_id",
        Uuid(),
        ForeignKey("app.source_versions.id", ondelete="RESTRICT"),
        nullable=False,
    ),
    Column("verified_on", Date(), nullable=False),
    Column("valid_from", Date(), nullable=False),
    Column("valid_to", Date()),
    Column("active", Boolean(), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    PrimaryKeyConstraint("id"),
    UniqueConstraint(
        "locality_id",
        "concern_category",
        "locale",
        "organisation",
        name="uq_escalation_routes_scope",
        postgresql_nulls_not_distinct=True,
    ),
    Index("ix_escalation_routes_locality_id", "locality_id"),
    Index("ix_escalation_routes_source_version_id", "source_version_id"),
    schema="app",
)
