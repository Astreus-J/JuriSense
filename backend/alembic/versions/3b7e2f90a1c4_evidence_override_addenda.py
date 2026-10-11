"""evidence_override_addenda: chained, anchorable override records

Revision ID: 3b7e2f90a1c4
Revises: 8f1c6ac4d2b7
Create Date: 2026-10-10 00:05:00.000000

Product decision (2026-10-10, #187). `override_decision` edits the `Decision` row in place
but never touched its `EvidencePackage` -- the anchored evidence stayed stale relative to the
real, overridden decision. This adds `evidence_override_addenda`: one row per override, chained
by `previous_hash` (so more than one override on the same package is itself tamper-evident and
ordered, not an independent bag of rows -- `app/evidence/domain/override_addendum.py`), guarded
by the same append-only trigger #184 added for the other evidence tables.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "3b7e2f90a1c4"
down_revision: Union[str, Sequence[str], None] = "8f1c6ac4d2b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "evidence_override_addenda",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "organization_id", sa.Uuid(), sa.ForeignKey("organizations.id"), nullable=False
        ),
        sa.Column(
            "evidence_package_id",
            sa.Uuid(),
            sa.ForeignKey("evidence_packages.id"),
            nullable=False,
        ),
        sa.Column("decision_id", sa.Uuid(), sa.ForeignKey("decisions.id"), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("original_status", sa.String(length=20), nullable=False),
        sa.Column("new_status", sa.String(length=20), nullable=False),
        sa.Column("justification", sa.Text(), nullable=False),
        sa.Column("overridden_by", sa.Uuid(), nullable=False),
        sa.Column("overridden_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("previous_hash", sa.String(length=64), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint(
            "evidence_package_id",
            "sequence_number",
            name="uq_evidence_override_addenda_one_per_sequence",
        ),
    )
    op.create_index(
        "ix_evidence_override_addenda_organization_id",
        "evidence_override_addenda",
        ["organization_id"],
    )
    op.create_index(
        "ix_evidence_override_addenda_evidence_package_id",
        "evidence_override_addenda",
        ["evidence_package_id"],
    )
    op.create_index(
        "ix_evidence_override_addenda_decision_id",
        "evidence_override_addenda",
        ["decision_id"],
    )
    op.execute(
        "CREATE TRIGGER trg_evidence_override_addenda_append_only "
        "BEFORE UPDATE OR DELETE ON evidence_override_addenda "
        "FOR EACH ROW EXECUTE FUNCTION reject_append_only_mutation();"
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_evidence_override_addenda_append_only "
        "ON evidence_override_addenda;"
    )
    op.drop_index(
        "ix_evidence_override_addenda_decision_id", table_name="evidence_override_addenda"
    )
    op.drop_index(
        "ix_evidence_override_addenda_evidence_package_id",
        table_name="evidence_override_addenda",
    )
    op.drop_index(
        "ix_evidence_override_addenda_organization_id", table_name="evidence_override_addenda"
    )
    op.drop_table("evidence_override_addenda")
