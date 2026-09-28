"""BR-ORG-001: a User may hold Memberships in more than one Organization.

STORY-0.2.5. There is no API surface yet for a user to self-service join a second
organization (that is the org-switcher, FEATURE-1.2/STORY-1.2.1) — this test exercises
the repository/domain layer directly to confirm the schema and the existing
organization-scoped query pattern both already support it correctly.
"""

import httpx
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.identity.domain.constants import MembershipStatus, Role
from app.identity.infrastructure.models import Membership
from app.identity.infrastructure.repositories import (
    MembershipRepository,
    OrganizationRepository,
    UserRepository,
)

ORG_1 = {
    "organization_name": "Org One",
    "full_name": "Ana Silva",
    "email": "ana@example.com",
    "password": "StrongPass1",
}

ORG_2 = {
    "organization_name": "Org Two",
    "full_name": "Someone Else",
    "email": "someone-else@example.com",
    "password": "StrongPass1",
}


async def test_user_can_hold_memberships_in_two_organizations(
    client: httpx.AsyncClient, db_session_factory: async_sessionmaker
) -> None:
    await client.post("/api/auth/register", json=ORG_1)
    await client.post("/api/auth/register", json=ORG_2)

    async with db_session_factory() as session:
        user_repo = UserRepository(session)
        org_repo = OrganizationRepository(session)
        membership_repo = MembershipRepository(session)

        ana = await user_repo.get_by_email(ORG_1["email"])
        other_admin = await user_repo.get_by_email(ORG_2["email"])
        org_2 = await org_repo.get_by_id(other_admin.organization_id)

        # Ana already has a Membership in Org One (created at registration). Simulate her
        # also consulting for Org Two, e.g. as a Viewer, by adding a second Membership.
        membership_repo.add(
            Membership(
                user_id=ana.id,
                organization_id=org_2.id,
                role=Role.VIEWER.value,
                status=MembershipStatus.ACTIVE.value,
            )
        )
        await session.commit()

        memberships = await membership_repo.list_by_user(ana.id)
        assert {m.organization_id for m in memberships} == {ana.organization_id, org_2.id}

        # Every permission check is scoped to exactly one Membership at a time
        # (BR-ORG-001): each organization's membership listing only ever returns the
        # membership relevant to that one organization, never the other.
        org_1_memberships = await membership_repo.list_by_organization(ana.organization_id)
        org_2_memberships = await membership_repo.list_by_organization(org_2.id)

        assert {m.user_id for m in org_1_memberships} == {ana.id}
        assert {m.user_id for m in org_2_memberships} == {ana.id, other_admin.id}
        assert next(m for m in org_1_memberships if m.user_id == ana.id).role == Role.ADMIN.value
        assert next(m for m in org_2_memberships if m.user_id == ana.id).role == Role.VIEWER.value

        # The existing organization-scoped User query pattern also keeps scoping
        # correctly: Ana's "home" organization_id column is unaffected by the second
        # Membership, and Org Two's user listing does not pick her up through it.
        org_2_users = await user_repo.list_by_organization(org_2.id)
        assert ana.id not in {u.id for u in org_2_users}
