"""FEATURE-6.1 default-workflow seeding: a fresh organization registration must have
`medium`/`high`/`critical` `ApprovalWorkflow` rows afterward -- so routing never has to
special-case "no workflow configured" for a brand-new org
(`app.identity.application.auth_service.register_organization`'s call into
`app.approvals.application.workflow_service.seed_default_workflows`).
"""

import httpx
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.approvals.infrastructure.repositories import ApprovalWorkflowRepository
from app.identity.infrastructure.repositories import OrganizationRepository, UserRepository
from tests.approvals.conftest import register_org_and_login


async def test_registering_an_organization_seeds_default_approval_workflows(
    client: httpx.AsyncClient, db_session_factory: async_sessionmaker
) -> None:
    headers = await register_org_and_login(client, "seed-workflows@example.com")

    async with db_session_factory() as session:
        admin = await UserRepository(session).get_by_email("seed-workflows@example.com")
        assert admin is not None
        organization = await OrganizationRepository(session).get_by_id(admin.organization_id)
        assert organization is not None

        workflows = await ApprovalWorkflowRepository(session).list_by_organization(
            organization.id
        )

    by_tier = {w.trigger_condition: w.steps for w in workflows}
    assert by_tier == {
        "medium": ["legal"],
        "high": ["compliance", "legal", "director"],
        "critical": ["compliance", "legal", "director"],
    }
    # Explicitly no "low" row (docs/03-domain/approvals.md: an undocumented edge case).
    assert "low" not in by_tier

    # Sanity: `headers` really is a usable bearer token from this registration (keeps
    # this test from silently passing on a broken register_org_and_login helper).
    me = await client.get("/api/auth/me", headers=headers)
    assert me.status_code == 200, me.text
