"""risks.policy_id -- disambiguate Risk.category collisions across Policies (#179)

Revision ID: c3ce7fde07a0
Revises: 3b7e2f90a1c4
Create Date: 2026-10-12 00:00:00.000000

Product decision (2026-10-12, #179). `Risk.category` (= the triggering rule's `rule_key`) is
only unique PER `PolicyVersion` (`uq_rule_key_per_version`) -- two different, independently-
authored Policies in the same organization can legitimately reuse the same `rule_key` string,
and `compliance_review_service.execute_review` pools rules across every currently-published
Policy, so this is a real (if rare) authoring collision, not hypothetical. Adds `policy_id` so
every Risk row carries its owning Policy explicitly, without changing what `category` means.

Backfilled via the one join that can recover it for existing rows: a Risk's `category` is the
`rule_key` of the `RuleEvaluation` that produced it, for the same `compliance_review_id`
(`compliance_review_service._RISK_OUTCOMES` derives exactly one Risk per REVIEW/BLOCK
RuleEvaluation) -> `RuleEvaluation.rule_id` -> `Rule.policy_version_id` -> `PolicyVersion.
policy_id`.

Security review (2026-10-12): correlating on `(compliance_review_id, rule_key)` alone is
ambiguous in the exact scenario this column exists to disambiguate -- if two different
Policies' rules share one `rule_key` and both got pooled into the SAME review
(`execute_review`'s multi-policy pooling), there are two matching `RuleEvaluation` rows, and
the original `LIMIT 1` with no `ORDER BY` could pick either one for both resulting `Risk`
rows. `severity`/`description` are also copied 1:1 from the same `RuleEvaluation` (`severity`,
`rationale`) at creation time (`compliance_review_service.execute_review`), so adding them to
the join's `WHERE` narrows the match to the exact originating row in every realistic case --
two rules would need an identical `rule_key`, `severity`, AND full rationale text to still
collide, which only happens if they are the same rule. Confirmed against the real dev
database (2026-10-12) that this ambiguity did not actually occur in any pre-existing row (the
only real `rule_key` collision found was across two separate reviews, not the same one), so no
re-backfill was needed there -- this tightens the SQL for correctness in any environment where
it could.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "c3ce7fde07a0"
down_revision: Union[str, Sequence[str], None] = "3b7e2f90a1c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("risks", sa.Column("policy_id", sa.Uuid(), nullable=True))
    op.execute(
        "UPDATE risks SET policy_id = ("
        "SELECT policy_versions.policy_id "
        "FROM rule_evaluations "
        "JOIN rules ON rules.id = rule_evaluations.rule_id "
        "JOIN policy_versions ON policy_versions.id = rules.policy_version_id "
        "WHERE rule_evaluations.compliance_review_id = risks.compliance_review_id "
        "AND rule_evaluations.rule_key = risks.category "
        "AND rule_evaluations.severity = risks.severity "
        "AND rule_evaluations.rationale = risks.description "
        "LIMIT 1"
        ")"
    )
    op.alter_column("risks", "policy_id", existing_type=sa.Uuid(), nullable=False)
    op.create_foreign_key("fk_risks_policy_id", "risks", "policies", ["policy_id"], ["id"])
    op.create_index("ix_risks_policy_id", "risks", ["policy_id"])


def downgrade() -> None:
    op.drop_index("ix_risks_policy_id", table_name="risks")
    op.drop_constraint("fk_risks_policy_id", "risks", type_="foreignkey")
    op.drop_column("risks", "policy_id")
