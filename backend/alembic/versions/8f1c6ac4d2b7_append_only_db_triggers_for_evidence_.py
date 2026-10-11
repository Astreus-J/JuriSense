"""append-only DB triggers for evidence_packages, evidence and audit_events

Revision ID: 8f1c6ac4d2b7
Revises: bce663ad384c
Create Date: 2026-10-10 00:00:00.000000

Product decision (2026-10-10, #184). `audit_events`, `evidence_packages` and `evidence` were
append-only only by repository convention (no update/delete method exposed) -- nothing in the
database itself stopped a raw UPDATE/DELETE from mutating or erasing anchored evidence. This adds
a `BEFORE UPDATE OR DELETE` trigger per table that unconditionally rejects the operation.

`blockchain_anchors` is deliberately NOT covered: `anchoring_service._refresh_from_provider`
legitimately updates `status`/`proof`/`confirmed_at` in place as a submission resolves, so that
table keeps only application-layer enforcement.

Mirrors `app/evidence/infrastructure/append_only.py`, which attaches the same trigger (via a
SQLite-compatible equivalent) to `Base.metadata`'s `after_create`/`before_create` events so the
test suite's `create_all()` exercises the identical invariant.
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8f1c6ac4d2b7"
down_revision: Union[str, Sequence[str], None] = "bce663ad384c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = ("audit_events", "evidence_packages", "evidence")


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
    op.execute("DROP FUNCTION IF EXISTS reject_append_only_mutation();")
