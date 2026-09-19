"""Metadata for ``app.idempotency_records`` so autogenerate can check the migration against it.

The table is reached only through the SECURITY DEFINER functions in revision 0002; no
application role holds a privilege on it.
"""

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Index,
    Integer,
    LargeBinary,
    PrimaryKeyConstraint,
    Table,
    Text,
    UniqueConstraint,
    Uuid,
)

from shaidago.db.metadata import metadata

idempotency_records = Table(
    "idempotency_records",
    metadata,
    Column("id", Uuid(), nullable=False),
    Column("operation", Text(), nullable=False),
    Column("key_hash", LargeBinary(), nullable=False),
    Column("fingerprint", LargeBinary(), nullable=False),
    Column("state", Text(), nullable=False),
    Column("response_status", Integer()),
    Column("sealed_response", LargeBinary()),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("sealed_until", DateTime(timezone=True), nullable=False),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    PrimaryKeyConstraint("id"),
    UniqueConstraint("operation", "key_hash"),
    CheckConstraint("state IN ('in_progress', 'completed')", name="state"),
    CheckConstraint("state <> 'completed' OR response_status IS NOT NULL", name="completed_status"),
    Index("ix_idempotency_records_expires_at", "expires_at"),
    schema="app",
)
