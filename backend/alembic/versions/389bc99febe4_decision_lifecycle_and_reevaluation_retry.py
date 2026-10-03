"""decision lifecycle (single effective decision per contract version) and re-evaluation retry

Revision ID: 389bc99febe4
Revises: 14121545bb15
Create Date: 2026-10-03 14:00:00.000000

FEATURE-6.5 (BR-DEC-002, BR-DEC-004). Adds:
- decisions.contract_version_id (denormalised from compliance_reviews, backfilled here),
- decisions.lifecycle ('ACTIVE' | 'SUPERSEDED'), backfilled from the existing supersedes chain
  and "newest Decision per contract version",
- a partial unique index so at most one ACTIVE Decision exists per contract version,
- retry bookkeeping: last_reevaluation_review_id, reevaluation_generation, reevaluation_failed_at.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "389bc99febe4"
down_revision: Union[str, Sequence[str], None] = "14121545bb15"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ACTIVE_PREDICATE = "lifecycle = 'ACTIVE'"


def upgrade() -> None:
    # contract_version_id: every existing review already carries one, so backfill then lock.
    op.add_column("decisions", sa.Column("contract_version_id", sa.Uuid(), nullable=True))
    op.execute(
        "UPDATE decisions SET contract_version_id = ("
        "SELECT compliance_reviews.contract_version_id FROM compliance_reviews "
        "WHERE compliance_reviews.id = decisions.compliance_review_id)"
    )
    op.alter_column("decisions", "contract_version_id", existing_type=sa.Uuid(), nullable=False)
    op.create_foreign_key(
        "fk_decisions_contract_version_id",
        "decisions",
        "contract_versions",
        ["contract_version_id"],
        ["id"],
    )

    # lifecycle: a Decision that a newer one names as its predecessor is SUPERSEDED; so is any
    # Decision that is not the newest for its contract version (the newest, ties broken by id,
    # is the one effective Decision). Everything else stays ACTIVE. This leaves at most one
    # ACTIVE row per contract version, so the partial unique index below can be created.
    op.add_column(
        "decisions",
        sa.Column("lifecycle", sa.String(length=20), server_default="ACTIVE", nullable=False),
    )
    op.execute(
        "UPDATE decisions SET lifecycle = 'SUPERSEDED' WHERE id IN ("
        "SELECT supersedes_decision_id FROM decisions WHERE supersedes_decision_id IS NOT NULL)"
    )
    op.execute(
        "UPDATE decisions SET lifecycle = 'SUPERSEDED' WHERE EXISTS ("
        "SELECT 1 FROM decisions AS newer "
        "WHERE newer.contract_version_id = decisions.contract_version_id "
        "AND (newer.created_at > decisions.created_at "
        "OR (newer.created_at = decisions.created_at AND newer.id > decisions.id)))"
    )
    op.create_index(
        "uq_decisions_one_active_per_contract_version",
        "decisions",
        ["contract_version_id"],
        unique=True,
        postgresql_where=sa.text(ACTIVE_PREDICATE),
        sqlite_where=sa.text(ACTIVE_PREDICATE),
    )

    op.add_column("decisions", sa.Column("last_reevaluation_review_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_decisions_last_reevaluation_review_id",
        "decisions",
        "compliance_reviews",
        ["last_reevaluation_review_id"],
        ["id"],
    )
    op.add_column(
        "decisions",
        sa.Column("reevaluation_generation", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "decisions",
        sa.Column("reevaluation_failed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("decisions", "reevaluation_failed_at")
    op.drop_column("decisions", "reevaluation_generation")
    op.drop_constraint("fk_decisions_last_reevaluation_review_id", "decisions", type_="foreignkey")
    op.drop_column("decisions", "last_reevaluation_review_id")
    op.drop_index("uq_decisions_one_active_per_contract_version", table_name="decisions")
    op.drop_column("decisions", "lifecycle")
    op.drop_constraint("fk_decisions_contract_version_id", "decisions", type_="foreignkey")
    op.drop_column("decisions", "contract_version_id")
