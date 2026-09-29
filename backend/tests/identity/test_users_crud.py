"""User CRUD: org scoping, logical deactivation."""

import uuid

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.evidence.infrastructure.models import AuditEvent
from app.identity.infrastructure.repositories import MembershipRepository, UserRepository

REGISTRATION = {
    "organization_name": "Example Corp",
    "full_name": "Ana Silva",
    "email": "ana@example.com",
    "password": "StrongPass1",
    "plan": "business",
}

NEW = {
    "full_name": "Bruno Souza",
    "email": "bruno@example.com",
    "password": "StrongPass2",
    "role": "legal",
}


async def _admin_headers(client: httpx.AsyncClient, email: str = "ana@example.com") -> dict:
    await client.post(
        "/api/auth/register",
        json={**REGISTRATION, "email": email, "organization_name": f"Org of {email}"},
    )
    login = await client.post(
        "/api/auth/login", json={"email": email, "password": REGISTRATION["password"]}
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


async def test_listing_scoped_by_organization(client: httpx.AsyncClient) -> None:
    headers_a = await _admin_headers(client, "admin-a@example.com")
    headers_b = await _admin_headers(client, "admin-b@example.com")
    await client.post("/api/users", json=NEW, headers=headers_a)

    list_a = (await client.get("/api/users", headers=headers_a)).json()
    list_b = (await client.get("/api/users", headers=headers_b)).json()

    assert {u["email"] for u in list_a} == {"admin-a@example.com", "bruno@example.com"}
    assert {u["email"] for u in list_b} == {"admin-b@example.com"}


async def test_get_user_from_another_org_returns_404(client: httpx.AsyncClient) -> None:
    headers_a = await _admin_headers(client, "admin-a@example.com")
    headers_b = await _admin_headers(client, "admin-b@example.com")
    created = (await client.post("/api/users", json=NEW, headers=headers_a)).json()

    own = await client.get(f"/api/users/{created['id']}", headers=headers_a)
    other = await client.get(f"/api/users/{created['id']}", headers=headers_b)

    assert own.status_code == 200
    assert other.status_code == 404


async def test_update_user(client: httpx.AsyncClient) -> None:
    headers = await _admin_headers(client)
    created = (await client.post("/api/users", json=NEW, headers=headers)).json()

    response = await client.patch(
        f"/api/users/{created['id']}",
        json={"full_name": "Bruno S. Updated", "role": "compliance"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["full_name"] == "Bruno S. Updated"
    assert response.json()["role"] == "compliance"


async def test_logical_deactivation(client: httpx.AsyncClient) -> None:
    headers = await _admin_headers(client)
    created = (await client.post("/api/users", json=NEW, headers=headers)).json()

    response = await client.delete(f"/api/users/{created['id']}", headers=headers)
    assert response.status_code == 204

    # No physical deletion: the user is still listable, with inactive status
    detail = (await client.get(f"/api/users/{created['id']}", headers=headers)).json()
    assert detail["status"] == "inactive"
    assert detail["is_active"] is False

    # And can no longer authenticate
    login = await client.post(
        "/api/auth/login", json={"email": NEW["email"], "password": NEW["password"]}
    )
    assert login.status_code == 401


async def test_admin_cannot_deactivate_self(client: httpx.AsyncClient) -> None:
    headers = await _admin_headers(client)
    me = (await client.get("/api/auth/me", headers=headers)).json()

    response = await client.delete(f"/api/users/{me['id']}", headers=headers)
    assert response.status_code == 400


async def test_create_user_also_creates_a_membership(
    client: httpx.AsyncClient, db_session_factory: async_sessionmaker
) -> None:
    """Regression: admin-created users must be BR-ORG-001-provable via Membership too,
    not just via User.organization_id -- create_user used to skip this (only
    register_organization/accept_invitation created one)."""
    headers = await _admin_headers(client)
    created = (await client.post("/api/users", json=NEW, headers=headers)).json()

    async with db_session_factory() as session:
        membership = await MembershipRepository(session).get_by_user_and_organization(
            uuid.UUID(created["id"]), uuid.UUID(created["organization_id"])
        )
        assert membership is not None
        assert membership.role == NEW["role"]
        assert membership.status == "active"


async def test_update_user_syncs_membership_role_and_status(
    client: httpx.AsyncClient, db_session_factory: async_sessionmaker
) -> None:
    """Regression: PATCH /api/users/{id} used to update only the User row, leaving its
    Membership row's role/status permanently out of sync."""
    headers = await _admin_headers(client)
    created = (await client.post("/api/users", json=NEW, headers=headers)).json()

    await client.patch(f"/api/users/{created['id']}", json={"role": "compliance"}, headers=headers)
    async with db_session_factory() as session:
        membership = await MembershipRepository(session).get_by_user_and_organization(
            uuid.UUID(created["id"]), uuid.UUID(created["organization_id"])
        )
        assert membership.role == "compliance"

    await client.delete(f"/api/users/{created['id']}", headers=headers)
    async with db_session_factory() as session:
        membership = await MembershipRepository(session).get_by_user_and_organization(
            uuid.UUID(created["id"]), uuid.UUID(created["organization_id"])
        )
        assert membership.status == "revoked"

    await client.patch(f"/api/users/{created['id']}", json={"status": "active"}, headers=headers)
    async with db_session_factory() as session:
        membership = await MembershipRepository(session).get_by_user_and_organization(
            uuid.UUID(created["id"]), uuid.UUID(created["organization_id"])
        )
        assert membership.status == "active"
        user = await UserRepository(session).get_by_id(uuid.UUID(created["id"]))
        assert user.is_active is True


async def test_role_change_emits_user_updated_audit_event(
    client: httpx.AsyncClient, db_session_factory: async_sessionmaker
) -> None:
    """Regression: role/status changes via PATCH /api/users/{id} used to leave no audit
    trail at all -- the one Identity mutation missing an AuditEvent, unlike every sibling
    use case (registration, invitation, deactivation)."""
    headers = await _admin_headers(client)
    created = (await client.post("/api/users", json=NEW, headers=headers)).json()

    await client.patch(f"/api/users/{created['id']}", json={"role": "compliance"}, headers=headers)

    async with db_session_factory() as session:
        events = (
            (
                await session.execute(
                    select(AuditEvent).where(AuditEvent.event_type == "user.updated")
                )
            )
            .scalars()
            .all()
        )
        assert len(events) == 1
        assert events[0].payload["user_id"] == created["id"]
        assert events[0].payload["role"] == {"from": "legal", "to": "compliance"}
        assert "status" not in events[0].payload


async def test_reactivation_respects_plan_limit(client: httpx.AsyncClient) -> None:
    # Business plan (5 users): fill it up, deactivate one, replace it, then try to reactivate
    headers = await _admin_headers(client, "full@example.com")
    created = []
    for i in range(4):
        r = await client.post(
            "/api/users",
            json={**NEW, "email": f"member{i}@example.com"},
            headers=headers,
        )
        created.append(r.json())
    # Business plan: 5 active (admin + 4). Deactivate one and create a replacement.
    await client.delete(f"/api/users/{created[0]['id']}", headers=headers)
    r = await client.post(
        "/api/users", json={**NEW, "email": "replacement@example.com"}, headers=headers
    )
    assert r.status_code == 201

    # Reactivating the deactivated one would exceed the limit of 5
    reactivate = await client.patch(
        f"/api/users/{created[0]['id']}", json={"status": "active"}, headers=headers
    )
    assert reactivate.status_code == 402
