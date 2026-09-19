"""A cited fact may be public while it is still awaiting verification (BE-041).

Revision ID: 0025_public_awaiting
Revises: 0024_public_run_query

`ck_project_facts_public_complete` refused to publish a fact whose verification state was
`awaiting_verification`. The product brief requires the opposite: "the interface should show when
information was last checked and when a claim is incomplete, disputed, outdated, or awaiting
verification", and it lists "Awaiting verification" as one of the public verification states. With
the old rule, a project whose only evidence is a single media report showed no facts at all, so the
public page said nothing rather than saying honestly what was reported and what is unconfirmed.

Nothing about evidence is relaxed. A public fact still needs `published_at`, still needs an
effective or last-checked date, and the `facts_public_citation` constraint trigger still requires at
least one citation to an approved source version. What changes is only that the honest label
`awaiting_verification` is publishable instead of being hidden.
"""

from alembic import op

from shaidago.db.migration_helpers import use_owner_role

revision = "0025_public_awaiting"
down_revision = "0024_public_run_query"
branch_labels = None
depends_on = None

CONSTRAINT = "ck_project_facts_public_complete"
NEW_RULE = """
    visibility = 'draft'
    OR (
        published_at IS NOT NULL
        AND (effective_on IS NOT NULL OR last_checked_on IS NOT NULL)
    )
"""
OLD_RULE = """
    visibility = 'draft'
    OR (
        published_at IS NOT NULL
        AND verification_state <> 'awaiting_verification'
        AND (effective_on IS NOT NULL OR last_checked_on IS NOT NULL)
    )
"""


def upgrade() -> None:
    use_owner_role()
    op.execute(f"ALTER TABLE app.project_facts DROP CONSTRAINT {CONSTRAINT}")
    op.execute(f"ALTER TABLE app.project_facts ADD CONSTRAINT {CONSTRAINT} CHECK ({NEW_RULE})")


def downgrade() -> None:
    use_owner_role()
    # Facts published while awaiting verification are returned to draft first, because the old rule
    # forbids them; their citations and history are untouched.
    op.execute(
        "UPDATE app.project_facts SET visibility = 'draft', published_at = NULL "
        "WHERE visibility = 'public' AND verification_state = 'awaiting_verification'"
    )
    op.execute(f"ALTER TABLE app.project_facts DROP CONSTRAINT {CONSTRAINT}")
    op.execute(f"ALTER TABLE app.project_facts ADD CONSTRAINT {CONSTRAINT} CHECK ({OLD_RULE})")
