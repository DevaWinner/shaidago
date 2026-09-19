"""Reviewer follow-up questions and private reporter answers (BE-067, ADR-0003, ADR-0004).

Revision ID: 0013_follow_up_answers
Revises: 0012_reporter_handles

A reviewer asks a question about one report; the reporter answers it, skips it, or says it is not
safe to answer. Answers are AES-GCM ciphertext under their own data key, so one answer can be
crypto-shredded alone. The public role has no privilege on either table: submission runs through
one ``SECURITY DEFINER`` function that proves the question belongs to a report the caller holds
(by tracking-code digest or verified handle), stores at most one answer per question, and applies
the state machine's ``record_follow_up`` transition when the last open question is answered.
Tracking sees questions and an acknowledgement state, never an answer.
"""

from alembic import op

from shaidago.db.migration_helpers import use_owner_role

revision = "0013_follow_up_answers"
down_revision = "0012_reporter_handles"
branch_labels = None
depends_on = None

QUESTIONS = """
CREATE TABLE app.report_follow_up_questions (
    id uuid NOT NULL,
    report_id uuid NOT NULL,
    question text NOT NULL,
    asked_by uuid,
    asked_at timestamptz NOT NULL,
    withdrawn_at timestamptz,
    CONSTRAINT pk_report_follow_up_questions PRIMARY KEY (id),
    CONSTRAINT uq_report_follow_up_questions_id_report_id UNIQUE (id, report_id),
    CONSTRAINT fk_report_follow_up_questions_report_id_reports
        FOREIGN KEY (report_id) REFERENCES app.reports (id) ON DELETE CASCADE,
    CONSTRAINT fk_report_follow_up_questions_asked_by_reviewers
        FOREIGN KEY (asked_by) REFERENCES app.reviewers (id) ON DELETE SET NULL,
    CONSTRAINT ck_report_follow_up_questions_question CHECK (
        char_length(question) BETWEEN 5 AND 500)
)
"""
ANSWERS = """
CREATE TABLE app.report_follow_up_answers (
    id uuid NOT NULL,
    question_id uuid NOT NULL,
    report_id uuid NOT NULL,
    kind text NOT NULL,
    answer_ciphertext bytea,
    data_key_id uuid,
    schema_version integer NOT NULL,
    created_at timestamptz NOT NULL,
    CONSTRAINT pk_report_follow_up_answers PRIMARY KEY (id),
    CONSTRAINT uq_report_follow_up_answers_question_id UNIQUE (question_id),
    CONSTRAINT fk_report_follow_up_answers_question
        FOREIGN KEY (question_id, report_id)
        REFERENCES app.report_follow_up_questions (id, report_id) ON DELETE CASCADE,
    CONSTRAINT fk_report_follow_up_answers_data_key_id_data_keys
        FOREIGN KEY (data_key_id) REFERENCES app.data_keys (id) ON DELETE RESTRICT,
    CONSTRAINT ck_report_follow_up_answers_kind CHECK (kind IN ('answered', 'skipped', 'unsafe')),
    CONSTRAINT ck_report_follow_up_answers_content CHECK (
        (kind = 'answered' AND answer_ciphertext IS NOT NULL AND data_key_id IS NOT NULL
         AND octet_length(answer_ciphertext) BETWEEN 29 AND 16384)
        OR (kind <> 'answered' AND answer_ciphertext IS NULL AND data_key_id IS NULL)),
    CONSTRAINT ck_report_follow_up_answers_schema_version CHECK (schema_version >= 1)
)
"""
SUBMIT = """
CREATE FUNCTION app.follow_up_submit(
    p_question_id uuid, p_lookup_hmacs bytea[], p_handle_id uuid, p_answer_id uuid,
    p_kind text, p_ciphertext bytea, p_key_id uuid, p_schema_version integer,
    p_now timestamptz, p_event_id uuid, p_audit_id uuid, p_message text)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, app AS $$
DECLARE
    target_report uuid;
    current_status text;
BEGIN
    -- Ownership: the question's report must be the one the caller's credential resolves to.
    SELECT q.report_id, r.status INTO target_report, current_status
    FROM app.report_follow_up_questions q
    JOIN app.reports r ON r.id = q.report_id
    WHERE q.id = p_question_id
      AND q.withdrawn_at IS NULL
      AND cardinality(coalesce(p_lookup_hmacs, ARRAY[]::bytea[])) <= 8
      AND ((p_handle_id IS NOT NULL AND r.reporter_handle_id = p_handle_id)
           OR EXISTS (SELECT 1 FROM app.report_tracking_keys k
                      WHERE k.report_id = r.id AND k.lookup_hmac = ANY (p_lookup_hmacs)))
    FOR UPDATE OF q, r;
    IF NOT FOUND THEN
        RETURN false;
    END IF;
    INSERT INTO app.report_follow_up_answers
        (id, question_id, report_id, kind, answer_ciphertext, data_key_id, schema_version,
         created_at)
    VALUES (p_answer_id, p_question_id, target_report, p_kind, p_ciphertext, p_key_id,
            p_schema_version, p_now)
    ON CONFLICT (question_id) DO NOTHING;
    IF NOT FOUND THEN
        RETURN false;  -- already answered, including by a concurrent request
    END IF;
    IF current_status = 'needs_information' AND NOT EXISTS (
        SELECT 1 FROM app.report_follow_up_questions q2
        WHERE q2.report_id = target_report AND q2.withdrawn_at IS NULL
          AND NOT EXISTS (SELECT 1 FROM app.report_follow_up_answers a2
                          WHERE a2.question_id = q2.id)) THEN
        INSERT INTO app.report_status_events
            (id, report_id, previous_status, new_status, public_message, actor_type, occurred_at)
        VALUES (p_event_id, target_report, 'needs_information', 'under_review', p_message,
                'reporter', p_now);
        UPDATE app.reports SET status = 'under_review', status_updated_at = p_now,
            updated_at = p_now WHERE id = target_report;
    END IF;
    INSERT INTO app.audit_events
        (id, occurred_at, actor_type, event, subject_type, subject_id, outcome, details)
    VALUES (p_audit_id, p_now, 'reporter', 'report_follow_up_received', 'report', target_report,
            'success', jsonb_build_object('kind', p_kind));
    RETURN true;
END
$$
"""
TRACKING_QUESTIONS = """
CREATE FUNCTION app.tracking_follow_ups(p_lookup_hmacs bytea[])
RETURNS TABLE (question_id uuid, question text, state text)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, app AS $$
    SELECT q.id, q.question,
           CASE WHEN a.id IS NULL THEN 'open' WHEN a.kind = 'answered' THEN 'answered'
                WHEN a.kind = 'skipped' THEN 'skipped' ELSE 'unsafe' END
    FROM app.report_tracking_keys k
    JOIN app.report_follow_up_questions q ON q.report_id = k.report_id
    LEFT JOIN app.report_follow_up_answers a ON a.question_id = q.id
    WHERE cardinality(p_lookup_hmacs) BETWEEN 1 AND 8
      AND k.lookup_hmac = ANY (p_lookup_hmacs) AND q.withdrawn_at IS NULL
    ORDER BY q.asked_at, q.id
    LIMIT 10
$$
"""
SUBMIT_SIGNATURE = (
    "app.follow_up_submit(uuid, bytea[], uuid, uuid, text, bytea, uuid, integer, "
    "timestamptz, uuid, uuid, text)"
)
TRACKING_SIGNATURE = "app.tracking_follow_ups(bytea[])"


def _guard(table: str) -> None:
    target = f"app.{table}"
    op.execute(f"ALTER TABLE {target} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {target} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"CREATE POLICY {table}_owner_all ON {target} TO shaidago_owner "
        "USING (true) WITH CHECK (true)"
    )
    op.execute(
        f"CREATE POLICY {table}_reviewer_all ON {target} TO shaidago_reviewer "
        "USING (true) WITH CHECK (true)"
    )
    op.execute(f"GRANT SELECT ON {target} TO shaidago_reviewer")


def upgrade() -> None:
    use_owner_role()
    op.execute(QUESTIONS)
    op.execute(ANSWERS)
    op.execute(
        "CREATE INDEX ix_report_follow_up_questions_report_id "
        "ON app.report_follow_up_questions (report_id, asked_at)"
    )
    _guard("report_follow_up_questions")
    _guard("report_follow_up_answers")
    # Reviewers author and withdraw questions; they never write answers.
    op.execute("GRANT INSERT ON app.report_follow_up_questions TO shaidago_reviewer")
    op.execute("GRANT UPDATE (withdrawn_at) ON app.report_follow_up_questions TO shaidago_reviewer")
    for ddl, signature in ((SUBMIT, SUBMIT_SIGNATURE), (TRACKING_QUESTIONS, TRACKING_SIGNATURE)):
        op.execute(ddl)
        op.execute(f"REVOKE EXECUTE ON FUNCTION {signature} FROM PUBLIC")
        op.execute(f"GRANT EXECUTE ON FUNCTION {signature} TO shaidago_public")


def downgrade() -> None:
    use_owner_role()
    op.execute(f"DROP FUNCTION {TRACKING_SIGNATURE}")
    op.execute(f"DROP FUNCTION {SUBMIT_SIGNATURE}")
    op.execute("DROP TABLE app.report_follow_up_answers")
    op.execute("DROP TABLE app.report_follow_up_questions")
