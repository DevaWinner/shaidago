"""A private, encrypted reason on each reviewer status event (BE-071, ADR-0004).

Revision ID: 0015_status_event_reason
Revises: 0014_reviewer_queue

The reporter-facing ``public_message`` stays plain text and is the only thing tracking reads. The
internal reason a reviewer gives for a decision is ciphertext under its own data key, in the same
append-only row, so it cannot be edited later, cannot leak through the tracking projection, and
can be crypto-shredded on its own.
"""

from alembic import op

from shaidago.db.migration_helpers import use_owner_role

revision = "0015_status_event_reason"
down_revision = "0014_reviewer_queue"
branch_labels = None
depends_on = None


def upgrade() -> None:
    use_owner_role()
    op.execute(
        "ALTER TABLE app.report_status_events "
        "ADD COLUMN reason_ciphertext bytea, ADD COLUMN reason_key_id uuid, "
        "ADD COLUMN reason_schema_version integer, "
        "ADD CONSTRAINT fk_report_status_events_reason_key_id_data_keys "
        "FOREIGN KEY (reason_key_id) REFERENCES app.data_keys (id) ON DELETE RESTRICT, "
        "ADD CONSTRAINT ck_report_status_events_reason CHECK ("
        "(reason_ciphertext IS NULL AND reason_key_id IS NULL AND reason_schema_version IS NULL) "
        "OR (reason_ciphertext IS NOT NULL AND reason_key_id IS NOT NULL "
        "AND reason_schema_version >= 1 AND octet_length(reason_ciphertext) BETWEEN 29 AND 16384 "
        "AND actor_type IN ('reviewer', 'admin')))"
    )


def downgrade() -> None:
    use_owner_role()
    op.execute(
        "ALTER TABLE app.report_status_events "
        "DROP CONSTRAINT ck_report_status_events_reason, "
        "DROP CONSTRAINT fk_report_status_events_reason_key_id_data_keys, "
        "DROP COLUMN reason_schema_version, DROP COLUMN reason_key_id, "
        "DROP COLUMN reason_ciphertext"
    )
