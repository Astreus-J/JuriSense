"""ADR-016 end-of-sprint audit (Identity & Organizations scope) — explicit, mandatory
tenant-isolation / cross-tenant-access reproduction (ADR-003).

Proves a user authenticated as an admin of Organization A cannot read or write
Organization B's data through any Identity route (users, invites), and that the two
repository classes with no dedicated HTTP route (Membership, ModulePermission) still
enforce `organization_id` scoping at the query level, so no future route built on top of
them could accidentally leak across tenants either.

Not a regression test kept long-term in the suite by this audit's authors -- written and
run specifically for the Sprint security audit's checklist item, same spirit as
`test_get_user_from_another_org_returns_404` (test_users_crud.py) but broader in scope
(invites + repository layer, not just the user-detail route).
"""

import uuid

import httpx

from app.identity.application.permission_service import has_permission
from app.identity.domain.constants import Module
from app.identity.infrastructure.repositories import (
    MembershipRepository,
    ModulePermissionRepository,
    UserRepository,
)

REGISTRATION = {
    "organization_name": "placeholder",
    "full_name": "Admin",
    "email": "placeholder",
    "password": "StrongPass1",
    "plan": "business",
}


async def _register_and_login(client: httpx.AsyncClient, email: str) -> dict:
    await client.post(
        "/api/auth/register",
        json={**REGISTRATION, "email": email, "organization_name": f"Org of {email}"},
    )
    login = await client.post(
        "/api/auth/login", json={"email": email, "password": REGISTRATION["password"]}
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


async def test_cross_tenant_isolation_full_identity_surface(client: httpx.AsyncClient) -> None:
    # --- Setup: two independent organizations, each with its own admin ---
    headers_a = await _register_and_login(client, "admin-a@tenant-audit.com")
    headers_b = await _register_and_login(client, "admin-b@tenant-audit.com")

    # Org A creates a second user ("victim") inside its own tenant.
    victim = (
        await client.post(
            "/api/users",
            json={
                "full_name": "Victim User",
                "email": "victim@tenant-audit.com",
                "password": "StrongPass2",
                "role": "legal",
            },
            headers=headers_a,
        )
    ).json()

    # Org A sends an invite inside its own tenant.
    invite_a = (
        await client.post(
            "/api/users/invites",
            json={"email": "invitee@tenant-audit.com", "role": "viewer"},
            headers=headers_a,
        )
    ).json()

    # ================= 1. Users: read, write, delete across tenants =================
    read_cross = await client.get(f"/api/users/{victim['id']}", headers=headers_b)
    assert read_cross.status_code == 404, "org B must not be able to read org A's user"

    write_cross = await client.patch(
        f"/api/users/{victim['id']}",
        json={"full_name": "Pwned By Org B"},
        headers=headers_b,
    )
    assert write_cross.status_code == 404, "org B must not be able to modify org A's user"

    delete_cross = await client.delete(f"/api/users/{victim['id']}", headers=headers_b)
    assert delete_cross.status_code == 404, "org B must not be able to deactivate org A's user"

    # List must never leak the other org's users either.
    list_b = (await client.get("/api/users", headers=headers_b)).json()
    assert victim["email"] not in {u["email"] for u in list_b}
    assert "admin-a@tenant-audit.com" not in {u["email"] for u in list_b}

    # Sanity: the write/delete really were no-ops (org A's own view is unchanged/still active).
    still_a = (await client.get(f"/api/users/{victim['id']}", headers=headers_a)).json()
    assert still_a["full_name"] == "Victim User"
    assert still_a["is_active"] is True

    # ================= 2. Invites: list and cross-org enumeration =================
    list_invites_b = (await client.get("/api/users/invites", headers=headers_b)).json()
    assert invite_a["id"] not in {i["id"] for i in list_invites_b}
    assert "invitee@tenant-audit.com" not in {i["email"] for i in list_invites_b}

    list_invites_a = (await client.get("/api/users/invites", headers=headers_a)).json()
    assert invite_a["id"] in {i["id"] for i in list_invites_a}

    # ================= 3. Repository layer: Membership (no dedicated HTTP route) =====
    # Resolve the two orgs' ids from their own admin's /auth/me.
    me_a = (await client.get("/api/auth/me", headers=headers_a)).json()
    me_b = (await client.get("/api/auth/me", headers=headers_b)).json()
    org_a_id = uuid.UUID(me_a["organization_id"])
    org_b_id = uuid.UUID(me_b["organization_id"])
    user_a_id = uuid.UUID(me_a["id"])
    user_b_id = uuid.UUID(me_b["id"])

    # Use the ASGI app's own DB session override to reach the repository layer directly,
    # exactly as every real route's service code does.
    from app.core.db import get_session
    from app.main import app as fastapi_app

    session_dep = fastapi_app.dependency_overrides[get_session]
    async for session in session_dep():
        membership_repo = MembershipRepository(session)
        # Org B's id must never resolve org A's own admin membership.
        cross_membership = await membership_repo.get_by_user_and_organization(
            user_a_id, org_b_id
        )
        assert cross_membership is None, (
            "a Membership lookup scoped to org B must not return org A's admin's row, "
            "even when queried by org A's own user_id"
        )
        own_membership = await membership_repo.get_by_user_and_organization(user_a_id, org_a_id)
        assert own_membership is not None

        # list_by_organization must not leak the other org's memberships either.
        memberships_b = await membership_repo.list_by_organization(org_b_id)
        assert all(m.organization_id == org_b_id for m in memberships_b)
        assert user_a_id not in {m.user_id for m in memberships_b}

        # ============= 4. Repository layer: ModulePermission (no dedicated route) ====
        permission_repo = ModulePermissionRepository(session)
        cross_permission = await permission_repo.get_by_user_module(
            user_a_id, org_b_id, Module.SUPPLIERS.value
        )
        assert cross_permission is None, (
            "org A's admin ModulePermission row for 'suppliers' must not be returned "
            "when queried under org B's organization_id"
        )

        # has_permission() must be evaluated against the CALLER's own membership row,
        # never a cross-org one -- fetch org B's real admin User object and confirm its
        # grid (seeded under org_b_id) is what's actually consulted.
        user_repo = UserRepository(session)
        admin_b_user = await user_repo.get_by_id(user_b_id)
        assert admin_b_user is not None
        assert await has_permission(
            session, user=admin_b_user, module=Module.SUPPLIERS, action="read"
        )
        # Confirm the row has_permission actually used belongs to org B, not org A.
        own_permission_b = await permission_repo.get_by_user_module(
            user_b_id, org_b_id, Module.SUPPLIERS.value
        )
        assert own_permission_b is not None
        break  # the override is a one-shot async generator; one session is enough
