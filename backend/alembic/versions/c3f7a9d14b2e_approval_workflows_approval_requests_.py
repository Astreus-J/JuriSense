"""approval workflows, approval requests, decisions

Revision ID: c3f7a9d14b2e
Revises: 1eea9eb23b17
Create Date: 2026-10-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3f7a9d14b2e'
down_revision: Union[str, Sequence[str], None] = '1eea9eb23b17'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('approval_workflows',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('organization_id', sa.Uuid(), nullable=False),
    sa.Column('trigger_condition', sa.String(length=20), nullable=False),
    sa.Column('steps', sa.JSON(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_approval_workflows_organization_id'), 'approval_workflows', ['organization_id'], unique=False)
    op.create_index('ix_approval_workflows_org_trigger_condition', 'approval_workflows', ['organization_id', 'trigger_condition'], unique=False)

    op.create_table('approval_requests',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('organization_id', sa.Uuid(), nullable=False),
    sa.Column('compliance_review_id', sa.Uuid(), nullable=False),
    sa.Column('approval_workflow_id', sa.Uuid(), nullable=False),
    sa.Column('approver_role', sa.String(length=50), nullable=False),
    sa.Column('step_number', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('justification', sa.Text(), nullable=True),
    sa.Column('resolved_by', sa.Uuid(), nullable=True),
    sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('requested_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['approval_workflow_id'], ['approval_workflows.id'], ),
    sa.ForeignKeyConstraint(['compliance_review_id'], ['compliance_reviews.id'], ),
    sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
    sa.ForeignKeyConstraint(['resolved_by'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_approval_requests_organization_id'), 'approval_requests', ['organization_id'], unique=False)
    op.create_index(op.f('ix_approval_requests_compliance_review_id'), 'approval_requests', ['compliance_review_id'], unique=False)
    op.create_index(op.f('ix_approval_requests_approval_workflow_id'), 'approval_requests', ['approval_workflow_id'], unique=False)
    op.create_index('ix_approval_requests_org_review', 'approval_requests', ['organization_id', 'compliance_review_id'], unique=False)

    op.create_table('decisions',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('organization_id', sa.Uuid(), nullable=False),
    sa.Column('compliance_review_id', sa.Uuid(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('valid_until', sa.DateTime(timezone=True), nullable=False),
    sa.Column('supersedes_decision_id', sa.Uuid(), nullable=True),
    sa.Column('overridden', sa.Boolean(), nullable=False),
    sa.Column('override_justification', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['compliance_review_id'], ['compliance_reviews.id'], ),
    sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
    sa.ForeignKeyConstraint(['supersedes_decision_id'], ['decisions.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_decisions_organization_id'), 'decisions', ['organization_id'], unique=False)
    op.create_index(op.f('ix_decisions_compliance_review_id'), 'decisions', ['compliance_review_id'], unique=False)
    op.create_index('ix_decisions_org_review', 'decisions', ['organization_id', 'compliance_review_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_decisions_org_review', table_name='decisions')
    op.drop_index(op.f('ix_decisions_compliance_review_id'), table_name='decisions')
    op.drop_index(op.f('ix_decisions_organization_id'), table_name='decisions')
    op.drop_table('decisions')

    op.drop_index('ix_approval_requests_org_review', table_name='approval_requests')
    op.drop_index(op.f('ix_approval_requests_approval_workflow_id'), table_name='approval_requests')
    op.drop_index(op.f('ix_approval_requests_compliance_review_id'), table_name='approval_requests')
    op.drop_index(op.f('ix_approval_requests_organization_id'), table_name='approval_requests')
    op.drop_table('approval_requests')

    op.drop_index('ix_approval_workflows_org_trigger_condition', table_name='approval_workflows')
    op.drop_index(op.f('ix_approval_workflows_organization_id'), table_name='approval_workflows')
    op.drop_table('approval_workflows')
