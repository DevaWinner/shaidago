"""Idempotency records and their SECURITY DEFINER access functions (ADR-0005, ADR-0003).

Revision ID: 0002_idempotency_records
Revises: 0001_baseline

Application roles receive EXECUTE on the functions only, never a privilege on the table, so the
insert-only public role can claim and replay keys without being able to read any record.
"""

import sqlalchemy as sa
from alembic import op

from shaidago.db.migration_helpers import use_owner_role

revision = "0002_idempotency_records"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None

CLAIM_FUNCTION = """
CREATE FUNCTION app.idempotency_claim(
    p_operation text, p_key_hash bytea, p_fingerprint bytea, p_id uuid,
    p_now timestamptz, p_sealed_until timestamptz, p_expires_at timestamptz)
RETURNS TABLE (outcome text, response_status integer, sealed_response bytea)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, app AS $$
DECLARE
    existing app.idempotency_records%ROWTYPE;
BEGIN
    -- A concurrent duplicate blocks here until the first transaction commits or rolls back.
    INSERT INTO app.idempotency_records
        (id, operation, key_hash, fingerprint, state, created_at, sealed_until, expires_at)
    VALUES
        (p_id, p_operation, p_key_hash, p_fingerprint, 'in_progress', p_now, p_sealed_until,
         p_expires_at)
    ON CONFLICT (operation, key_hash) DO NOTHING;
    IF FOUND THEN
        RETURN QUERY SELECT 'claimed'::text, NULL::integer, NULL::bytea;
        RETURN;
    END IF;

    SELECT * INTO existing FROM app.idempotency_records r
    WHERE r.operation = p_operation AND r.key_hash = p_key_hash FOR UPDATE;

    IF existing.expires_at <= p_now THEN
        -- Retention is over: the key is treated as brand new.
        UPDATE app.idempotency_records r
        SET id = p_id, fingerprint = p_fingerprint, state = 'in_progress',
            response_status = NULL, sealed_response = NULL, created_at = p_now,
            sealed_until = p_sealed_until, expires_at = p_expires_at
        WHERE r.operation = p_operation AND r.key_hash = p_key_hash;
        RETURN QUERY SELECT 'claimed'::text, NULL::integer, NULL::bytea;
    ELSIF existing.fingerprint <> p_fingerprint THEN
        RETURN QUERY SELECT 'conflict'::text, NULL::integer, NULL::bytea;
    ELSIF existing.state = 'in_progress' THEN
        RETURN QUERY SELECT 'in_progress'::text, NULL::integer, NULL::bytea;
    ELSIF existing.sealed_until > p_now AND existing.sealed_response IS NOT NULL THEN
        RETURN QUERY SELECT 'replay'::text, existing.response_status, existing.sealed_response;
    ELSE
        RETURN QUERY SELECT 'already_received'::text, NULL::integer, NULL::bytea;
    END IF;
END
$$
"""

COMPLETE_FUNCTION = """
CREATE FUNCTION app.idempotency_complete(
    p_operation text, p_key_hash bytea, p_status integer, p_sealed bytea)
RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, app AS $$
BEGIN
    UPDATE app.idempotency_records r
    SET state = 'completed', response_status = p_status, sealed_response = p_sealed
    WHERE r.operation = p_operation AND r.key_hash = p_key_hash AND r.state = 'in_progress';
    IF NOT FOUND THEN
        RAISE EXCEPTION 'idempotency record was not claimed' USING ERRCODE = 'P0002';
    END IF;
END
$$
"""

PURGE_FUNCTION = """
CREATE FUNCTION app.idempotency_purge(p_now timestamptz, p_batch integer)
RETURNS integer
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, app AS $$
DECLARE
    scrubbed integer;
    removed integer;
BEGIN
    UPDATE app.idempotency_records r SET sealed_response = NULL
    WHERE r.id IN (
        SELECT id FROM app.idempotency_records
        WHERE sealed_until <= p_now AND sealed_response IS NOT NULL LIMIT p_batch);
    GET DIAGNOSTICS scrubbed = ROW_COUNT;
    DELETE FROM app.idempotency_records r
    WHERE r.id IN (
        SELECT id FROM app.idempotency_records WHERE expires_at <= p_now LIMIT p_batch);
    GET DIAGNOSTICS removed = ROW_COUNT;
    RETURN scrubbed + removed;
END
$$
"""


def upgrade() -> None:
    use_owner_role()
    op.create_table(
        "idempotency_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("operation", sa.Text(), nullable=False),
        sa.Column("key_hash", sa.LargeBinary(), nullable=False),
        sa.Column("fingerprint", sa.LargeBinary(), nullable=False),
        sa.Column("state", sa.Text(), nullable=False),
        sa.Column("response_status", sa.Integer(), nullable=True),
        sa.Column("sealed_response", sa.LargeBinary(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sealed_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_idempotency_records")),
        sa.UniqueConstraint(
            "operation", "key_hash", name=op.f("uq_idempotency_records_operation_key_hash")
        ),
        sa.CheckConstraint(
            "state IN ('in_progress', 'completed')", name=op.f("ck_idempotency_records_state")
        ),
        sa.CheckConstraint(
            "state <> 'completed' OR response_status IS NOT NULL",
            name=op.f("ck_idempotency_records_completed_status"),
        ),
        schema="app",
    )
    op.create_index(
        "ix_idempotency_records_expires_at", "idempotency_records", ["expires_at"], schema="app"
    )
    # Only the owner (and the functions it owns) may touch the table; nobody else has a grant.
    op.execute("ALTER TABLE app.idempotency_records ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE app.idempotency_records FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY idempotency_owner_all ON app.idempotency_records "
        "TO shaidago_owner USING (true) WITH CHECK (true)"
    )
    op.execute(CLAIM_FUNCTION)
    op.execute(COMPLETE_FUNCTION)
    op.execute(PURGE_FUNCTION)
    # Explicit as well as via default privileges: nobody but the roles below may call these.
    op.execute(
        "REVOKE EXECUTE ON FUNCTION "
        "app.idempotency_claim(text, bytea, bytea, uuid, timestamptz, timestamptz, timestamptz), "
        "app.idempotency_complete(text, bytea, integer, bytea), "
        "app.idempotency_purge(timestamptz, integer) FROM PUBLIC"
    )
    op.execute(
        "GRANT EXECUTE ON FUNCTION "
        "app.idempotency_claim(text, bytea, bytea, uuid, timestamptz, timestamptz, timestamptz), "
        "app.idempotency_complete(text, bytea, integer, bytea) "
        "TO shaidago_public, shaidago_reviewer"
    )
    op.execute(
        "GRANT EXECUTE ON FUNCTION app.idempotency_purge(timestamptz, integer) TO shaidago_worker"
    )


def downgrade() -> None:
    use_owner_role()
    op.execute("DROP FUNCTION app.idempotency_purge(timestamptz, integer)")
    op.execute("DROP FUNCTION app.idempotency_complete(text, bytea, integer, bytea)")
    op.execute(
        "DROP FUNCTION app.idempotency_claim("
        "text, bytea, bytea, uuid, timestamptz, timestamptz, timestamptz)"
    )
    op.drop_index(
        "ix_idempotency_records_expires_at", table_name="idempotency_records", schema="app"
    )
    op.drop_table("idempotency_records", schema="app")
