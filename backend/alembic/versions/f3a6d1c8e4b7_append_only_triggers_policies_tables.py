"""append-only DB triggers for compliance_reviews, rule_evaluations, policy_exceptions

Revision ID: f3a6d1c8e4b7
Revises: 82a158e1840e
Create Date: 2026-10-12 00:00:00.000000

Security audit (2026-10-12): `compliance_reviews`, `rule_evaluations`, and `policy_exceptions`
were append-only only by repository convention (no update/delete method exposed) -- the same
gap `8f1c6ac4d2b7` (#184) closed for `audit_events`/`evidence_packages`/`evidence`, never
extended to these three. Reuses that migration's own `reject_append_only_mutation()` function
(`CREATE OR REPLACE`, so re-declaring it here is idempotent and safe regardless of which
migration runs first in a fresh environment).

Deliberately does NOT cover `decisions`: unlike these three, `Decision` has several genuine,
already-shipped in-place mutation paths (lifecycle transitions ACTIVE->SUPERSEDED, the
explicitly-modeled manual override, re-evaluation-attempt tracking) -- a blanket trigger would
break real, tested functionality. `policies`/`policy_versions`/`rules` are also excluded: they
are genuinely mutable while a `PolicyVersion` is still `draft`, not append-only from creation.
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f3a6d1c8e4b7"
down_revision: Union[str, Sequence[str], None] = "82a158e1840e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = ("compliance_reviews", "rule_evaluations", "policy_exceptions")


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION reject_append_only_mutation() RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION '% rows are append-only: % is not allowed', TG_TABLE_NAME, TG_OP;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    for table in TABLES:
        op.execute(
            f"CREATE TRIGGER trg_{table}_append_only "
            f"BEFORE UPDATE OR DELETE ON {table} "
            f"FOR EACH ROW EXECUTE FUNCTION reject_append_only_mutation();"
        )


def downgrade() -> None:
    for table in TABLES:
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_append_only ON {table};")
