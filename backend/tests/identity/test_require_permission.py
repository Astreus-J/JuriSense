"""STORY-1.1.2: the generic `require_permission(module, action)` dependency — deny by
default, and composes correctly with the tenant-scoping already enforced at the
repository layer (EPIC-0) rather than substituting for it.
"""

import uuid

import httpx
import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core import security
from app.identity.api.deps import require_permission
from app.identity.domain.constants import Module, Role
from app.identity.infrastructure.models import Organization, User


async def _admin_headers(client: httpx.AsyncClient, email: str) -> dict:
    await client.post(
        "/api/auth/register",
        json={
            "organization_name": f"Org of {email}",
            "full_name": "Admin",
            "email": email,
            "password": "StrongPass1",
            "plan": "business",
        },
    )
    login = await client.post("/api/auth/login", json={"email": email, "password": "StrongPass1"})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


async def _load_user(db_session_factory: async_sessionmaker, user_id: str) -> User:
    async with db_session_factory() as session:
        return await session.get(User, uuid.UUID(user_id))


async def test_admin_is_granted_full_access_by_require_permission(
    client: httpx.AsyncClient, db_session_factory: async_sessionmaker
) -> None:
    headers = await _admin_headers(client, "admin-full@example.com")
    me = await client.get("/api/auth/me", headers=headers)
    admin = await _load_user(db_session_factory, me.json()["id"])

    async with db_session_factory() as session:
        for module in Module:
            for action in ("create", "read", "update", "delete"):
                result = await require_permission(module, action)(admin, session)
                assert result is admin


async def test_viewer_cannot_write_to_any_module(
    client: httpx.AsyncClient, db_session_factory: async_sessionmaker
) -> None:
    headers = await _admin_headers(client, "admin-viewer@example.com")
    created = await client.post(
        "/api/users",
        json={
            "full_name": "Vera Viewer",
            "email": "vera@example.com",
            "password": "StrongPass1",
            "role": "viewer",
        },
        headers=headers,
    )
    viewer = await _load_user(db_session_factory, created.json()["id"])

    async with db_session_factory() as session:
        for module in Module:
            for action in ("create", "update", "delete"):
                with pytest.raises(HTTPException) as exc_info:
                    await require_permission(module, action)(viewer, session)
                assert exc_info.value.status_code == 403

        # Sanity: the same viewer CAN read the modules its default grid grants read on.
        allowed_read = await require_permission(Module.SUPPLIERS, "read")(viewer, session)
        assert allowed_read is viewer


async def test_user_with_no_persisted_grid_row_is_denied_by_default(
    db_session_factory: async_sessionmaker,
) -> None:
    """A `User` bypassing the normal creation flow (no seeded grid) must be refused, not
    implicitly allowed — the fail-closed half of ADR-012.
    """
    async with db_session_factory() as session:
        organization = Organization(name="No Grid Org")
        session.add(organization)
        await session.flush()
        user = User(
            organization_id=organization.id,
            full_name="No Grid",
            email="nogrid@example.com",
            password_hash=security.hash_password("StrongPass1"),
            role=Role.ADMIN.value,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        with pytest.raises(HTTPException) as exc_info:
            await require_permission(Module.SUPPLIERS, "read")(user, session)
        assert exc_info.value.status_code == 403


async def test_rbac_and_tenant_scoping_compose_no_org_can_read_another_orgs_data(
    client: httpx.AsyncClient, db_session_factory: async_sessionmaker
) -> None:
    """Combines both layers explicitly (STORY-1.1.2): the RBAC grid alone would allow org
    A's admin to read the `integrations` module (admin has full access to every module,
    regardless of which organization owns the data), yet the tenant-scoped repository/route
    still denies the specific cross-tenant record — proving the composition holds, not just
    each guard in isolation.
    """
    headers_a = await _admin_headers(client, "admin-a-tenant@example.com")
    headers_b = await _admin_headers(client, "admin-b-tenant@example.com")

    me_a = await client.get("/api/auth/me", headers=headers_a)
    admin_a = await _load_user(db_session_factory, me_a.json()["id"])

    # RBAC layer: admin A's grid does allow reading the `integrations` module.
    async with db_session_factory() as session:
        allowed = await require_permission(Module.INTEGRATIONS, "read")(admin_a, session)
        assert allowed is admin_a

    # Org B creates an integration.
    created = await client.post(
        "/api/integrations", json={"provider": "docusign", "config": {}}, headers=headers_b
    )
    integration_id = created.json()["id"]

    # Tenant-scoping layer: org A's admin — despite being RBAC-allowed on this module —
    # still cannot read org B's integration through the real route (404, never a
    # cross-tenant-existence-confirming 403, per coding-standards.md).
    cross_tenant_read = await client.get(f"/api/integrations/{integration_id}", headers=headers_a)
    assert cross_tenant_read.status_code == 404

    # Org A itself sees only its own (empty) list.
    own_list = await client.get("/api/integrations", headers=headers_a)
    assert own_list.json() == []
