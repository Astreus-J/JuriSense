"""STORY-2.1/2.2: Supplier registration (SUP-001, BR-SUP-001, BR-SUP-002) and tenant-
scoped list/detail (STORY-2.2). `stub_supplier_check_enqueue` (conftest, autouse) means
no real SupplierCheck runs in these tests — they only exercise the Supplier record
itself.
"""

import httpx

from tests.suppliers.conftest import register_org_and_login


async def test_create_supplier(client: httpx.AsyncClient) -> None:
    headers = await register_org_and_login(client, "procurement-a@example.com")

    response = await client.post(
        "/api/suppliers",
        json={"legal_name": "Acme Ltda", "tax_id": "00.000.000/0001-91", "jurisdiction": "BR"},
        headers=headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["legal_name"] == "Acme Ltda"
    # BR-SUP-002 comparisons are digits-only — the formatted CNPJ is normalized on write.
    assert body["tax_id"] == "00000000000191"
    assert body["status"] == "prospect"


async def test_duplicate_tax_id_in_same_organization_is_conflict(client: httpx.AsyncClient) -> None:
    headers = await register_org_and_login(client, "procurement-dup@example.com")
    payload = {"legal_name": "Acme Ltda", "tax_id": "00000000000191", "jurisdiction": "BR"}

    first = await client.post("/api/suppliers", json=payload, headers=headers)
    second = await client.post("/api/suppliers", json=payload, headers=headers)

    assert first.status_code == 201
    assert second.status_code == 409


async def test_same_tax_id_allowed_across_different_organizations(
    client: httpx.AsyncClient,
) -> None:
    """BR-SUP-002's uniqueness is per-organization, not global."""
    headers_a = await register_org_and_login(client, "org-a-dup@example.com")
    headers_b = await register_org_and_login(client, "org-b-dup@example.com")
    payload = {"legal_name": "Acme Ltda", "tax_id": "00000000000191", "jurisdiction": "BR"}

    response_a = await client.post("/api/suppliers", json=payload, headers=headers_a)
    response_b = await client.post("/api/suppliers", json=payload, headers=headers_b)

    assert response_a.status_code == 201
    assert response_b.status_code == 201


async def test_create_requires_authentication(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/api/suppliers", json={"legal_name": "Acme", "tax_id": "123", "jurisdiction": "BR"}
    )
    assert response.status_code == 401


async def test_viewer_role_cannot_create_supplier(client: httpx.AsyncClient) -> None:
    admin_headers = await register_org_and_login(client, "admin-viewer-sup@example.com")
    await client.post(
        "/api/users",
        json={
            "full_name": "Viewer",
            "email": "viewer-sup@example.com",
            "password": "StrongPass1",
            "role": "viewer",
        },
        headers=admin_headers,
    )
    login = await client.post(
        "/api/auth/login", json={"email": "viewer-sup@example.com", "password": "StrongPass1"}
    )
    viewer_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    response = await client.post(
        "/api/suppliers",
        json={"legal_name": "Acme", "tax_id": "111", "jurisdiction": "BR"},
        headers=viewer_headers,
    )
    assert response.status_code == 403


async def test_list_scoped_to_own_organization(client: httpx.AsyncClient) -> None:
    headers_a = await register_org_and_login(client, "list-a@example.com")
    headers_b = await register_org_and_login(client, "list-b@example.com")
    await client.post(
        "/api/suppliers",
        json={"legal_name": "Acme A", "tax_id": "11111111000111", "jurisdiction": "BR"},
        headers=headers_a,
    )

    listing_a = await client.get("/api/suppliers", headers=headers_a)
    listing_b = await client.get("/api/suppliers", headers=headers_b)

    assert len(listing_a.json()) == 1
    assert listing_b.json() == []


async def test_list_filters_by_status(client: httpx.AsyncClient) -> None:
    headers = await register_org_and_login(client, "status-filter@example.com")
    await client.post(
        "/api/suppliers",
        json={"legal_name": "Acme", "tax_id": "22222222000122", "jurisdiction": "BR"},
        headers=headers,
    )

    prospects = await client.get("/api/suppliers", params={"status": "prospect"}, headers=headers)
    blocked = await client.get("/api/suppliers", params={"status": "blocked"}, headers=headers)

    assert len(prospects.json()) == 1
    assert blocked.json() == []


async def test_get_supplier_from_another_org_returns_404(client: httpx.AsyncClient) -> None:
    headers_a = await register_org_and_login(client, "detail-a@example.com")
    headers_b = await register_org_and_login(client, "detail-b@example.com")
    created = (
        await client.post(
            "/api/suppliers",
            json={"legal_name": "Acme", "tax_id": "33333333000133", "jurisdiction": "BR"},
            headers=headers_a,
        )
    ).json()

    own = await client.get(f"/api/suppliers/{created['id']}", headers=headers_a)
    other = await client.get(f"/api/suppliers/{created['id']}", headers=headers_b)

    assert own.status_code == 200
    assert other.status_code == 404


async def test_get_unknown_supplier_returns_404(client: httpx.AsyncClient) -> None:
    headers = await register_org_and_login(client, "detail-404@example.com")
    response = await client.get(
        "/api/suppliers/00000000-0000-0000-0000-000000000000", headers=headers
    )
    assert response.status_code == 404
