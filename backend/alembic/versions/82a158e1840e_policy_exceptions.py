"""policy_exceptions table + rule_evaluations.exception_id (#120, STORY-4.4.2)

Revision ID: 82a158e1840e
Revises: c3ce7fde07a0
Create Date: 2026-10-12 00:00:00.000000

Adds the `PolicyException` table (a time-boxed, approver-signed waiver of one REVIEW-tier
Rule for one Supplier or ContractVersion) and `rule_evaluations.exception_id`, set only
when a `RuleEvaluation`'s outcome is `EXEMPTED` -- the exception that caused the rule to be
waived rather than CEL-evaluated. Both are brand-new, so no backfill is needed.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "82a158e1840e"
down_revision: Union[str, Sequence[str], None] = "c3ce7fde07a0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "policy_exceptions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("rule_id", sa.Uuid(), nullable=False),
        sa.Column("supplier_id", sa.Uuid(), nullable=True),
        sa.Column("contract_version_id", sa.Uuid(), nullable=True),
        sa.Column("justification", sa.Text(), nullable=False),
        sa.Column("approver_role", sa.String(length=50), nullable=False),
        sa.Column("granted_by", sa.Uuid(), nullable=False),
        sa.Column(
            "valid_from", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["rule_id"], ["rules.id"]),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"]),
        sa.ForeignKeyConstraint(["contract_version_id"], ["contract_versions.id"]),
        sa.ForeignKeyConstraint(["granted_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_policy_exceptions_organization_id", "policy_exceptions", ["organization_id"]
    )
    op.create_index("ix_policy_exceptions_rule_id", "policy_exceptions", ["rule_id"])
    op.create_index(
        "ix_policy_exceptions_rule_supplier", "policy_exceptions", ["rule_id", "supplier_id"]
    )
    op.create_index(
        "ix_policy_exceptions_rule_contract_version",
        "policy_exceptions",
        ["rule_id", "contract_version_id"],
    )

    op.add_column("rule_evaluations", sa.Column("exception_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_rule_evaluations_exception_id",
        "rule_evaluations",
        "policy_exceptions",
        ["exception_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_rule_evaluations_exception_id", "rule_evaluations", type_="foreignkey"
    )
    op.drop_column("rule_evaluations", "exception_id")

    op.drop_index("ix_policy_exceptions_rule_contract_version", table_name="policy_exceptions")
    op.drop_index("ix_policy_exceptions_rule_supplier", table_name="policy_exceptions")
    op.drop_index("ix_policy_exceptions_rule_id", table_name="policy_exceptions")
    op.drop_index("ix_policy_exceptions_organization_id", table_name="policy_exceptions")
    op.drop_table("policy_exceptions")
