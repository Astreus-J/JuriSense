"""GET /api/suppliers/{id}/profile: exposes the normalized SupplierProfile (SUP-003) --
until this endpoint existed, the only API-visible view of registry status/sanctions_hit
was buried inside a SupplierCheck's unstructured `raw_results`, which the supplier detail
screen (STORY-2.2) needs as a clean, typed shape.
"""

import httpx

from tests.suppliers.conftest import ACTIVE_CNPJ_RESPONSE, register_org_and_login


async def test_get_profile_after_successful_check(
    client: httpx.AsyncClient,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_supplier_checks_inline,
) -> None:
    mock_cnpj_registry(data=ACTIVE_CNPJ_RESPONSE)
    await seed_sanctions_index()
    headers = await register_org_and_login(client, "profile-get@example.com")

    created = (
        await client.post(
            "/api/suppliers",
            json={
                "legal_name": "Banco do Brasil SA",
                "tax_id": "00000000000191",
                "jurisdiction": "BR",
            },
            headers=headers,
        )
    ).json()

    response = await client.get(f"/api/suppliers/{created['id']}/profile", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["supplier_id"] == created["id"]
    assert body["registry_status"] == "active"
    assert body["sanctions_hit"] is False
    assert body["cnae_code"] == "6422100"


async def test_get_profile_404_before_any_check_completes(
    client: httpx.AsyncClient, mock_cnpj_registry, seed_sanctions_index
) -> None:
    """No `run_supplier_checks_inline` fixture here: the initial check stays queued, not
    completed, so no SupplierProfile exists yet -- must 404, never 200 with empty data."""
    mock_cnpj_registry(data=ACTIVE_CNPJ_RESPONSE)
    await seed_sanctions_index()
    headers = await register_org_and_login(client, "profile-pending@example.com")

    created = (
        await client.post(
            "/api/suppliers",
            json={
                "legal_name": "Banco do Brasil SA",
                "tax_id": "00000000000191",
                "jurisdiction": "BR",
            },
            headers=headers,
        )
    ).json()

    response = await client.get(f"/api/suppliers/{created['id']}/profile", headers=headers)
    assert response.status_code == 404


async def test_get_profile_404_for_another_organizations_supplier(
    client: httpx.AsyncClient,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_supplier_checks_inline,
) -> None:
    mock_cnpj_registry(data=ACTIVE_CNPJ_RESPONSE)
    await seed_sanctions_index()
    headers_a = await register_org_and_login(client, "profile-org-a@example.com")
    headers_b = await register_org_and_login(client, "profile-org-b@example.com")

    created = (
        await client.post(
            "/api/suppliers",
            json={
                "legal_name": "Banco do Brasil SA",
                "tax_id": "00000000000191",
                "jurisdiction": "BR",
            },
            headers=headers_a,
        )
    ).json()

    response = await client.get(f"/api/suppliers/{created['id']}/profile", headers=headers_b)
    assert response.status_code == 404
