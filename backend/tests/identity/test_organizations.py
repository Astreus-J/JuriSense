"""`GET /api/organizations/me`: the `/settings/organization` screen's plan/usage panel."""

import httpx

REGISTRATION = {
    "organization_name": "Growth Co",
    "full_name": "Ana Silva",
    "email": "ana@example.com",
    "password": "StrongPass1",
    "plan": "growth",
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


async def test_get_my_organization_returns_plan_limits_and_active_user_count(
    client: httpx.AsyncClient,
) -> None:
    headers = await _admin_headers(client, "growth-admin@example.com")

    response = await client.get("/api/organizations/me", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["plan"] == "growth"
    assert body["user_limit"] == 20
    assert body["supplier_limit"] == 5000
    assert body["storage_limit_gb"] == 300
    assert body["ai_execution_limit"] == 1000
    assert body["active_user_count"] == 1  # the admin created at registration

    await client.post(
        "/api/users",
        json={
            "full_name": "Second User",
            "email": "second@example.com",
            "password": "StrongPass2",
            "role": "legal",
        },
        headers=headers,
    )
    after_create = (await client.get("/api/organizations/me", headers=headers)).json()
    assert after_create["active_user_count"] == 2


async def test_get_my_organization_enterprise_plan_reports_unlimited_as_null(
    client: httpx.AsyncClient,
) -> None:
    """Regression guard for the Enterprise-limits bug fixed 2026-10-08: `None` here must
    mean "unlimited" end to end, API included -- not get silently coerced into a number."""
    await client.post(
        "/api/auth/register",
        json={**REGISTRATION, "email": "enterprise-admin@example.com", "plan": "enterprise"},
    )
    login = await client.post(
        "/api/auth/login",
        json={"email": "enterprise-admin@example.com", "password": REGISTRATION["password"]},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    response = await client.get("/api/organizations/me", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["plan"] == "enterprise"
    assert body["user_limit"] is None
    assert body["supplier_limit"] is None
    assert body["storage_limit_gb"] is None
    assert body["ai_execution_limit"] is None


async def test_security_role_can_read_organization_settings_per_rbac_grid(
    client: httpx.AsyncClient,
) -> None:
    """DEFAULT_ROLE_GRID (`rbac.py`) grants `security` read access to
    `organization_settings`, unlike every other non-admin role -- this endpoint must
    follow that real grid, not a hardcoded admin-only check."""
    admin_headers = await _admin_headers(client, "security-org-admin@example.com")
    await client.post(
        "/api/users",
        json={
            "full_name": "Security User",
            "email": "security-reader@example.com",
            "password": "StrongPass2",
            "role": "security",
        },
        headers=admin_headers,
    )
    login = await client.post(
        "/api/auth/login",
        json={"email": "security-reader@example.com", "password": "StrongPass2"},
    )
    security_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    response = await client.get("/api/organizations/me", headers=security_headers)
    assert response.status_code == 200, response.text


async def test_non_admin_cannot_read_organization_settings(client: httpx.AsyncClient) -> None:
    admin_headers = await _admin_headers(client, "viewer-admin@example.com")
    await client.post(
        "/api/users",
        json={
            "full_name": "Viewer User",
            "email": "viewer@example.com",
            "password": "StrongPass2",
            "role": "viewer",
        },
        headers=admin_headers,
    )
    login = await client.post(
        "/api/auth/login", json={"email": "viewer@example.com", "password": "StrongPass2"}
    )
    viewer_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    response = await client.get("/api/organizations/me", headers=viewer_headers)
    assert response.status_code == 403
