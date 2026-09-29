"""QA/security review (2026-09-29): SUP-001 requires "a jurisdiction-specific identifier
(CNPJ for Brazil)", but nothing validated its shape -- `POST /api/suppliers` accepted
garbage like `"not-a-cnpj"` or `"x"`, which then made BrasilAPI's 404 look like a
legitimate "registry status: unknown" outcome instead of a rejected input.
"""

import httpx

from tests.suppliers.conftest import register_org_and_login


async def test_create_supplier_rejects_a_non_numeric_tax_id(client: httpx.AsyncClient) -> None:
    headers = await register_org_and_login(client, "taxid-garbage@example.com")
    response = await client.post(
        "/api/suppliers",
        json={"legal_name": "Acme", "tax_id": "not-a-cnpj", "jurisdiction": "BR"},
        headers=headers,
    )
    assert response.status_code == 422


async def test_create_supplier_rejects_a_cnpj_that_fails_the_checksum(
    client: httpx.AsyncClient,
) -> None:
    headers = await register_org_and_login(client, "taxid-bad-checksum@example.com")
    response = await client.post(
        "/api/suppliers",
        # Same digit count as a real CNPJ, but not a real one (checksum mismatch).
        json={"legal_name": "Acme", "tax_id": "12345678000100", "jurisdiction": "BR"},
        headers=headers,
    )
    assert response.status_code == 422


async def test_create_supplier_rejects_all_repeated_digits(client: httpx.AsyncClient) -> None:
    """A same-digit string can accidentally satisfy the mod-11 arithmetic; the validator
    explicitly rejects it regardless."""
    headers = await register_org_and_login(client, "taxid-repeated@example.com")
    response = await client.post(
        "/api/suppliers",
        json={"legal_name": "Acme", "tax_id": "11111111111111", "jurisdiction": "BR"},
        headers=headers,
    )
    assert response.status_code == 422


async def test_create_supplier_accepts_a_valid_cnpj(client: httpx.AsyncClient) -> None:
    headers = await register_org_and_login(client, "taxid-valid@example.com")
    response = await client.post(
        "/api/suppliers",
        json={"legal_name": "Banco do Brasil SA", "tax_id": "00000000000191", "jurisdiction": "BR"},
        headers=headers,
    )
    assert response.status_code == 201


async def test_create_supplier_accepts_a_formatted_valid_cnpj(client: httpx.AsyncClient) -> None:
    """`_normalize_tax_id` strips punctuation before validation -- the classic
    '12.345.678/0001-90' formatting must still pass."""
    headers = await register_org_and_login(client, "taxid-formatted@example.com")
    response = await client.post(
        "/api/suppliers",
        json={
            "legal_name": "Banco do Brasil SA",
            "tax_id": "00.000.000/0001-91",
            "jurisdiction": "BR",
        },
        headers=headers,
    )
    assert response.status_code == 201
