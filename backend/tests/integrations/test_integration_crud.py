"""STORY-1.4.1: `Integration` is a configuration record only (no real connector), with
minimal, tenant-scoped CRUD gated by the caller's RBAC grid (STORY-1.1.2).
"""

import httpx


async def _admin_headers(client: httpx.AsyncClient, email: str) -> dict:
    await client.post(
        "/api/auth/register",
        json={
            "organization_name": f"Org of {email}",
            "full_name": "Admin",
            "email": email,
            "password": "StrongPass1",
            # Starter's user_limit is 1 (admin only); the RBAC tests below need headroom
            # to create a second user under the same org.
            "plan": "business",
        },
    )
    login = await client.post("/api/auth/login", json={"email": email, "password": "StrongPass1"})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


async def _user_headers_with_role(
    client: httpx.AsyncClient, admin_headers: dict, email: str, role: str
) -> dict:
    await client.post(
        "/api/users",
        json={"full_name": "Team Member", "email": email, "password": "StrongPass1", "role": role},
        headers=admin_headers,
    )
    login = await client.post("/api/auth/login", json={"email": email, "password": "StrongPass1"})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


async def test_create_and_get_integration(client: httpx.AsyncClient) -> None:
    headers = await _admin_headers(client, "admin-int-1@example.com")

    created = await client.post(
        "/api/integrations",
        json={"provider": "docusign", "config": {"api_key": "placeholder"}},
        headers=headers,
    )
    assert created.status_code == 201
    body = created.json()
    assert body["provider"] == "docusign"
    assert body["status"] == "configured"

    fetched = await client.get(f"/api/integrations/{body['id']}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json() == body


async def test_list_scoped_to_own_organization(client: httpx.AsyncClient) -> None:
    headers_a = await _admin_headers(client, "admin-int-a@example.com")
    headers_b = await _admin_headers(client, "admin-int-b@example.com")

    await client.post(
        "/api/integrations", json={"provider": "slack", "config": {}}, headers=headers_a
    )

    listing_a = await client.get("/api/integrations", headers=headers_a)
    listing_b = await client.get("/api/integrations", headers=headers_b)

    assert len(listing_a.json()) == 1
    assert listing_b.json() == []


async def test_create_requires_admin(client: httpx.AsyncClient) -> None:
    unauthenticated = await client.post(
        "/api/integrations", json={"provider": "slack", "config": {}}
    )
    assert unauthenticated.status_code == 401


async def test_get_unknown_integration_returns_404(client: httpx.AsyncClient) -> None:
    headers = await _admin_headers(client, "admin-int-404@example.com")
    response = await client.get(
        "/api/integrations/00000000-0000-0000-0000-000000000000", headers=headers
    )
    assert response.status_code == 404


async def test_security_role_can_read_but_not_create_integrations(
    client: httpx.AsyncClient,
) -> None:
    """Regression: routes originally gated on a hardcoded admin-only check, even though the
    default RBAC grid (rbac.py) explicitly grants `security` read access to `integrations`
    -- the routes now dogfood require_permission (STORY-1.1.2) instead."""
    admin_headers = await _admin_headers(client, "admin-int-rbac@example.com")
    created = await client.post(
        "/api/integrations", json={"provider": "slack", "config": {}}, headers=admin_headers
    )
    integration_id = created.json()["id"]

    security_headers = await _user_headers_with_role(
        client, admin_headers, "security-int@example.com", "security"
    )

    listing = await client.get("/api/integrations", headers=security_headers)
    assert listing.status_code == 200
    assert len(listing.json()) == 1

    fetched = await client.get(f"/api/integrations/{integration_id}", headers=security_headers)
    assert fetched.status_code == 200

    denied_create = await client.post(
        "/api/integrations", json={"provider": "docusign", "config": {}}, headers=security_headers
    )
    assert denied_create.status_code == 403


async def test_viewer_role_cannot_read_integrations(client: httpx.AsyncClient) -> None:
    """Viewer's default grid has no access to `integrations` at all (admin/security/auditor
    only) -- confirms require_permission denies roles the grid doesn't grant, not just
    roles it explicitly forbids."""
    admin_headers = await _admin_headers(client, "admin-int-viewer@example.com")
    viewer_headers = await _user_headers_with_role(
        client, admin_headers, "viewer-int@example.com", "viewer"
    )

    response = await client.get("/api/integrations", headers=viewer_headers)
    assert response.status_code == 403
