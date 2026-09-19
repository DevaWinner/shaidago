"""Tracking status lookup for the insert-only public role (BE-065, ADR-0003, ADR-0005).

Revision ID: 0011_tracking_lookup
Revises: 0010_private_reports

The public role cannot read any report table. One ``SECURITY DEFINER`` function takes the keyed
lookup digests of a tracking code (one per pepper version still accepted) and returns only the
current status, when it changed, and the newest reviewer-safe message. It returns no identifier,
no text, and nothing that says which pepper matched, and an absent code and a present one cost
the same single indexed probe.
"""

from alembic import op

from shaidago.db.migration_helpers import use_owner_role

revision = "0011_tracking_lookup"
down_revision = "0010_private_reports"
branch_labels = None
depends_on = None

MAX_CANDIDATES = 8
SIGNATURE = "app.tracking_lookup(bytea[])"
FUNCTION = f"""
CREATE FUNCTION app.tracking_lookup(p_lookup_hmacs bytea[])
RETURNS TABLE (status text, status_updated_at timestamptz, public_message text)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, app AS $$
    SELECT r.status, r.status_updated_at,
           (SELECT e.public_message FROM app.report_status_events e
            WHERE e.report_id = r.id ORDER BY e.occurred_at DESC, e.id DESC LIMIT 1)
    FROM app.report_tracking_keys k
    JOIN app.reports r ON r.id = k.report_id
    WHERE cardinality(p_lookup_hmacs) BETWEEN 1 AND {MAX_CANDIDATES}
      AND k.lookup_hmac = ANY (p_lookup_hmacs)
    LIMIT 1
$$
"""


def upgrade() -> None:
    use_owner_role()
    op.execute(FUNCTION)
    op.execute(f"REVOKE EXECUTE ON FUNCTION {SIGNATURE} FROM PUBLIC")
    op.execute(f"GRANT EXECUTE ON FUNCTION {SIGNATURE} TO shaidago_public")


def downgrade() -> None:
    use_owner_role()
    op.execute(f"DROP FUNCTION {SIGNATURE}")
