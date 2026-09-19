"""Imports every table module so its tables register on the shared metadata.

Alembic and drift tests import this module. Each task that adds a table module adds its import
here, in the same change as the migration that creates the table.
"""

from shaidago.db import (
    escalation_tables,
    idempotency_table,
    project_tables,
    reviewer_tables,
    source_tables,
)
from shaidago.db.metadata import metadata

__all__ = [
    "escalation_tables",
    "idempotency_table",
    "metadata",
    "project_tables",
    "reviewer_tables",
    "source_tables",
]
