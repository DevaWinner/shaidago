"""Metadata for wrapped data-encryption keys (BE-060). Checks and policies live in revision 0009."""

from sqlalchemy import (
    Column,
    DateTime,
    Index,
    LargeBinary,
    PrimaryKeyConstraint,
    Table,
    Text,
    UniqueConstraint,
    Uuid,
)

from shaidago.db.metadata import metadata

data_keys = Table(
    "data_keys",
    metadata,
    Column("id", Uuid(), nullable=False),
    Column("purpose", Text(), nullable=False),
    Column("owner_table", Text(), nullable=False),
    Column("owner_id", Uuid(), nullable=False),
    Column("wrapped_key", LargeBinary()),
    Column("kek_version", Text()),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("destroyed_at", DateTime(timezone=True)),
    PrimaryKeyConstraint("id"),
    UniqueConstraint("owner_table", "owner_id", "purpose"),
    Index("ix_data_keys_kek_version", "kek_version"),
    schema="app",
)
