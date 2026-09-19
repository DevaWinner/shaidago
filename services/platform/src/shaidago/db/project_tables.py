"""Metadata for localities, projects, and project translations (BE-040).

Check-constraint value lists are literal copies of ``contracts/controlled-vocabulary.json``;
``tests/unit/projects/test_vocabulary_parity.py`` fails if they diverge from it.
"""

from sqlalchemy import (
    ARRAY,
    CheckConstraint,
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
    text,
)

from shaidago.db.metadata import metadata

LOCALES = ("en", "ha", "ig", "yo")
LOCALITY_KINDS = ("state", "area_council")
PROJECT_CATEGORIES = (
    "health",
    "education",
    "water_sanitation",
    "roads_public_works",
    "other_public_service",
)
PROJECT_PUBLIC_STATUSES = (
    "unknown",
    "planned",
    "procurement",
    "in_progress",
    "on_hold",
    "completed",
    "cancelled",
)
PROJECT_VISIBILITIES = ("public", "hidden")
TRANSLATION_STATUSES = ("reviewed", "machine_assisted", "unavailable")


def sql_in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(value) for value in values)})"


localities = Table(
    "localities",
    metadata,
    Column("id", Uuid(), nullable=False),
    Column("slug", Text(), nullable=False),
    Column("name", Text(), nullable=False),
    Column("kind", Text(), nullable=False),
    Column("parent_id", Uuid(), ForeignKey("app.localities.id", ondelete="RESTRICT")),
    Column("enabled_locales", ARRAY(Text()), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    PrimaryKeyConstraint("id"),
    UniqueConstraint("slug"),
    CheckConstraint(sql_in("kind", LOCALITY_KINDS), name="kind"),
    CheckConstraint("enabled_locales <@ ARRAY['en','ha','ig','yo']::text[]", name="locales"),
    CheckConstraint("'en' = ANY (enabled_locales)", name="source_locale"),
    CheckConstraint("slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'", name="slug_format"),
    schema="app",
)

projects = Table(
    "projects",
    metadata,
    Column("id", Uuid(), nullable=False),
    Column("slug", Text(), nullable=False),
    Column(
        "locality_id", Uuid(), ForeignKey("app.localities.id", ondelete="RESTRICT"), nullable=False
    ),
    Column("category", Text(), nullable=False),
    Column("public_status", Text(), nullable=False),
    Column("visibility", Text(), nullable=False),
    Column("last_checked_on", Date()),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    PrimaryKeyConstraint("id"),
    UniqueConstraint("slug"),
    CheckConstraint(sql_in("category", PROJECT_CATEGORIES), name="category"),
    CheckConstraint(sql_in("public_status", PROJECT_PUBLIC_STATUSES), name="public_status"),
    CheckConstraint(sql_in("visibility", PROJECT_VISIBILITIES), name="visibility"),
    CheckConstraint("slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'", name="slug_format"),
    # A check cannot be dated after the row that records it was written.
    CheckConstraint(
        "last_checked_on IS NULL OR "
        "last_checked_on <= (updated_at AT TIME ZONE 'Africa/Lagos')::date",
        name="last_checked_not_future",
    ),
    Index("ix_projects_locality_id", "locality_id"),
    schema="app",
)
# Serves the public list order (newest first) without a sort; see docs/evidence/BE-045.
Index(
    "ix_projects_public_recent",
    projects.c.updated_at.desc(),
    projects.c.id.desc(),
    postgresql_where=text("visibility = 'public'"),
)

project_translations = Table(
    "project_translations",
    metadata,
    Column("id", Uuid(), nullable=False),
    Column("project_id", Uuid(), ForeignKey("app.projects.id", ondelete="CASCADE"), nullable=False),
    Column("locale", Text(), nullable=False),
    Column("title", Text(), nullable=False),
    Column("summary", Text(), nullable=False),
    Column("promised_deliverable", Text(), nullable=False),
    Column("translation_status", Text(), nullable=False),
    Column("reviewed_at", DateTime(timezone=True)),
    Column("reviewer_note", Text()),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    PrimaryKeyConstraint("id"),
    UniqueConstraint("project_id", "locale"),
    CheckConstraint(sql_in("locale", LOCALES), name="locale"),
    CheckConstraint(sql_in("translation_status", TRANSLATION_STATUSES), name="status"),
    CheckConstraint(
        "translation_status <> 'reviewed' OR reviewed_at IS NOT NULL", name="reviewed_has_date"
    ),
    CheckConstraint("title <> '' AND summary <> ''", name="text_not_empty"),
    schema="app",
)
# Serves the public full-text filter; the expression must match the query exactly.
Index(
    "ix_project_translations_search",
    text("to_tsvector('simple', title || ' ' || summary)"),
    postgresql_using="gin",
    _table=project_translations,
)
