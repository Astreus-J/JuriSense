"""Security/QA review (2026-09-29): `update_supplier_status` accepted any target status
from any current status -- e.g. `inactive -> prospect` or `approved -> prospect` -- because
only the `approved` target had a guard (BR-SUP-003). `ALLOWED_STATUS_TRANSITIONS`
(domain/constants.py) now enforces domain-model.md's documented lifecycle diagram as an
actual state machine.
"""

import httpx

from tests.suppliers.conftest import register_org_and_login

TAX_ID = "44444444000191"


async def _create_supplier(client: httpx.AsyncClient, headers: dict) -> dict:
    created = await client.post(
        "/api/suppliers",
        json={"legal_name": "Acme", "tax_id": TAX_ID, "jurisdiction": "BR"},
        headers=headers,
    )
    return created.json()


async def test_prospect_can_move_to_under_review_or_blocked(client: httpx.AsyncClient) -> None:
    headers = await register_org_and_login(client, "transition-prospect@example.com")
    created = await _create_supplier(client, headers)

    response = await client.patch(
        f"/api/suppliers/{created['id']}/status",
        json={"status": "under_review"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "under_review"


async def test_prospect_can_be_blocked_directly(client: httpx.AsyncClient) -> None:
    headers = await register_org_and_login(client, "transition-reject@example.com")
    created = await _create_supplier(client, headers)

    response = await client.patch(
        f"/api/suppliers/{created['id']}/status", json={"status": "blocked"}, headers=headers
    )
    assert response.status_code == 200


async def test_inactive_is_terminal(client: httpx.AsyncClient) -> None:
    headers = await register_org_and_login(client, "transition-terminal@example.com")
    created = await _create_supplier(client, headers)
    await client.patch(
        f"/api/suppliers/{created['id']}/status", json={"status": "blocked"}, headers=headers
    )
    await client.patch(
        f"/api/suppliers/{created['id']}/status", json={"status": "inactive"}, headers=headers
    )

    response = await client.patch(
        f"/api/suppliers/{created['id']}/status", json={"status": "prospect"}, headers=headers
    )
    assert response.status_code == 409


async def test_cannot_skip_backward_from_blocked_to_prospect(client: httpx.AsyncClient) -> None:
    headers = await register_org_and_login(client, "transition-backward@example.com")
    created = await _create_supplier(client, headers)
    await client.patch(
        f"/api/suppliers/{created['id']}/status", json={"status": "blocked"}, headers=headers
    )

    response = await client.patch(
        f"/api/suppliers/{created['id']}/status", json={"status": "prospect"}, headers=headers
    )
    assert response.status_code == 409


async def test_same_status_no_op_is_rejected(client: httpx.AsyncClient) -> None:
    headers = await register_org_and_login(client, "transition-noop@example.com")
    created = await _create_supplier(client, headers)

    response = await client.patch(
        f"/api/suppliers/{created['id']}/status", json={"status": "prospect"}, headers=headers
    )
    assert response.status_code == 409


async def test_approved_can_be_revoked_to_blocked(
    client: httpx.AsyncClient,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_supplier_checks_inline,
) -> None:
    from tests.suppliers.conftest import ACTIVE_CNPJ_RESPONSE

    mock_cnpj_registry(data=ACTIVE_CNPJ_RESPONSE)
    await seed_sanctions_index()
    headers = await register_org_and_login(client, "transition-revoke@example.com")
    created = await _create_supplier(client, headers)

    approved = await client.patch(
        f"/api/suppliers/{created['id']}/status", json={"status": "approved"}, headers=headers
    )
    assert approved.status_code == 200

    revoked = await client.patch(
        f"/api/suppliers/{created['id']}/status", json={"status": "blocked"}, headers=headers
    )
    assert revoked.status_code == 200
