"""Security review (2026-10-12): #181 only changed the seed template for brand-new
organizations -- an `ApprovalWorkflow` already persisted for an organization registered
before that fix still has the dead `"director"` role baked into its `steps`, and no real
user can ever hold that role. `backfill_director_role_to_approver` is the one-off repair
for rows that predate the fix.
"""

import httpx
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.approvals.application.workflow_service import backfill_director_role_to_approver
from app.approvals.infrastructure.repositories import ApprovalWorkflowRepository
from app.identity.infrastructure.repositories import UserRepository
from tests.approvals.conftest import register_org_and_login


async def test_backfill_replaces_director_with_approver_in_persisted_workflows(
    client: httpx.AsyncClient, db_session_factory: async_sessionmaker
) -> None:
    await register_org_and_login(client, "workflow-director-backfill@example.com")

    async with db_session_factory() as session:
        admin = await UserRepository(session).get_by_email(
            "workflow-director-backfill@example.com"
        )
        workflows = await ApprovalWorkflowRepository(session).list_by_organization(
            admin.organization_id
        )
        high = next(w for w in workflows if w.trigger_condition == "high")
        # Simulates a row seeded before #181's fix.
        high.steps = ["compliance", "legal", "director"]
        critical = next(w for w in workflows if w.trigger_condition == "critical")
        critical.steps = ["compliance", "legal", "director"]
        await session.commit()

    async with db_session_factory() as session:
        result = await backfill_director_role_to_approver(session)
    assert result.workflows_updated >= 2

    async with db_session_factory() as session:
        workflows = await ApprovalWorkflowRepository(session).list_by_organization(
            admin.organization_id
        )
    by_tier = {w.trigger_condition: w.steps for w in workflows}
    assert by_tier["high"] == ["compliance", "legal", "approver"]
    assert by_tier["critical"] == ["compliance", "legal", "approver"]
    assert by_tier["medium"] == ["legal"]  # untouched -- never contained "director"


async def test_backfill_is_idempotent_and_leaves_clean_workflows_untouched(
    client: httpx.AsyncClient, db_session_factory: async_sessionmaker
) -> None:
    await register_org_and_login(client, "workflow-director-backfill-clean@example.com")

    async with db_session_factory() as session:
        first = await backfill_director_role_to_approver(session)
    assert first.workflows_updated == 0  # freshly seeded orgs already say "approver"

    async with db_session_factory() as session:
        second = await backfill_director_role_to_approver(session)
    assert second.workflows_updated == 0
