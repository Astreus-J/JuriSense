"""re-evaluation sweep rotation (last_checked_at) and exception-path failure count

Revision ID: c5a1e0d7b92f
Revises: 389bc99febe4
Create Date: 2026-10-03 16:00:00.000000

FEATURE-6.5 review follow-up (F3, F4). Adds:
- decisions.last_checked_at: stamped on every sweep evaluation, so the candidate query can rotate
  through the backlog instead of re-reading the same oldest rows forever (sweep starvation). Nullable:
  a Decision never checked falls back to created_at in the ordering.
- decisions.reevaluation_failure_count: re-evaluation attempts that raised. Not NULL, default 0.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c5a1e0d7b92f"
down_revision: Union[str, Sequence[str], None] = "389bc99febe4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "decisions",
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "decisions",
        sa.Column(
            "reevaluation_failure_count", sa.Integer(), server_default="0", nullable=False
        ),
    )


def downgrade() -> None:
    op.drop_column("decisions", "reevaluation_failure_count")
    op.drop_column("decisions", "last_checked_at")
