"""User creation by the organization: admin only, own org, plan limit."""

import httpx

BASE_REGISTRATION = {
    "organization_name": "Example Corp",
    "full_name": "Ana Silva",
    "email": "ana@example.com",
    "password": "StrongPass1",
}

NEW_USER = {
    "full_name": "Bruno Souza",
    "email": "bruno@example.com",
    "password": "OtherPass1",
    "role": "legal",
}


async def _admin_headers(
    client: httpx.AsyncClient, plan: str = "business", email: str = "ana@example.com"
) -> dict[str, str]:
    """Registers an organization and returns the logged-in admin's Authorization header."""
    await client.post(
        "/api/auth/register", json={**BASE_REGISTRATION, "email": email, "plan": plan}
    )
    login = await client.post(
        "/api/auth/login", json={"email": email, "password": BASE_REGISTRATION["password"]}
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


async def test_create_user_requires_authentication(client: httpx.AsyncClient) -> None:
    response = await client.post("/api/users", json=NEW_USER)

    assert response.status_code == 401


async def test_admin_creates_user_in_own_org(client: httpx.AsyncClient) -> None:
    headers = await _admin_headers(client)

    response = await client.post("/api/users", json=NEW_USER, headers=headers)

    assert response.status_code == 201
    body = response.json()
    assert body["role"] == "legal"
    assert body["email"] == "bruno@example.com"

    me = await client.get("/api/auth/me", headers=headers)
    assert body["organization_id"] == me.json()["organization_id"]

    # The created user can authenticate
    login = await client.post(
        "/api/auth/login", json={"email": "bruno@example.com", "password": "OtherPass1"}
    )
    assert login.status_code == 200


async def test_non_admin_cannot_create_user(client: httpx.AsyncClient) -> None:
    headers = await _admin_headers(client)
    await client.post("/api/users", json=NEW_USER, headers=headers)

    login = await client.post(
        "/api/auth/login", json={"email": "bruno@example.com", "password": "OtherPass1"}
    )
    non_admin_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    response = await client.post(
        "/api/users",
        json={**NEW_USER, "email": "carla@example.com"},
        headers=non_admin_headers,
    )
    assert response.status_code == 403


async def test_plan_user_limit(client: httpx.AsyncClient) -> None:
    # Starter plan: 1 user — the admin already occupies the only seat
    headers = await _admin_headers(client, plan="starter")

    response = await client.post("/api/users", json=NEW_USER, headers=headers)

    assert response.status_code == 402
    assert "starter" in response.json()["detail"]
    assert "upgrade" in response.json()["detail"]


async def test_invalid_role_rejected(client: httpx.AsyncClient) -> None:
    headers = await _admin_headers(client)

    response = await client.post(
        "/api/users", json={**NEW_USER, "role": "superadmin"}, headers=headers
    )
    assert response.status_code == 422


async def test_duplicate_email_rejected(client: httpx.AsyncClient) -> None:
    headers = await _admin_headers(client)
    await client.post("/api/users", json=NEW_USER, headers=headers)

    duplicate = await client.post("/api/users", json=NEW_USER, headers=headers)

    assert duplicate.status_code == 409


async def test_payload_cannot_choose_organization(client: httpx.AsyncClient) -> None:
    """organization_id in the payload is ignored: the target is always the admin's org."""
    headers = await _admin_headers(client)

    response = await client.post(
        "/api/users",
        json={**NEW_USER, "organization_id": "00000000-0000-0000-0000-000000000000"},
        headers=headers,
    )

    assert response.status_code == 201
    me = await client.get("/api/auth/me", headers=headers)
    assert response.json()["organization_id"] == me.json()["organization_id"]
