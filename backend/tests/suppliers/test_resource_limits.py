"""Security audit (2026-10-12): per-organization resource-exhaustion backstop on
Suppliers -- unbounded creation was also unbounded cost (every creation triggers a real
CNPJ/sanctions check), the same gap #180 closed for Policies/PolicyVersions/Rules.
"""

import httpx
import pytest

from app.core.config import get_settings
from tests.suppliers.conftest import register_org_and_login


async def test_supplier_creation_is_refused_once_the_organization_limit_is_reached(
    client: httpx.AsyncClient,
    mock_cnpj_registry,
    seed_sanctions_index,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_cnpj_registry()
    await seed_sanctions_index()
    monkeypatch.setattr(get_settings(), "max_suppliers_per_organization", 1)
    headers = await register_org_and_login(client, "supplier-limit@example.com")

    first = await client.post(
        "/api/suppliers",
        json={"legal_name": "Acme A", "tax_id": "00000000000191", "jurisdiction": "BR"},
        headers=headers,
    )
    assert first.status_code == 201, first.text

    second = await client.post(
        "/api/suppliers",
        json={"legal_name": "Acme B", "tax_id": "11111111000191", "jurisdiction": "BR"},
        headers=headers,
    )
    assert second.status_code == 403, second.text
    assert "limit" in second.json()["detail"].lower()


async def test_supplier_creation_is_scoped_per_organization_not_global(
    client: httpx.AsyncClient,
    mock_cnpj_registry,
    seed_sanctions_index,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_cnpj_registry()
    await seed_sanctions_index()
    monkeypatch.setattr(get_settings(), "max_suppliers_per_organization", 1)

    a_headers = await register_org_and_login(client, "supplier-limit-org-a@example.com")
    b_headers = await register_org_and_login(client, "supplier-limit-org-b@example.com")

    a_created = await client.post(
        "/api/suppliers",
        json={"legal_name": "Acme A", "tax_id": "00000000000191", "jurisdiction": "BR"},
        headers=a_headers,
    )
    assert a_created.status_code == 201, a_created.text
    # Org A is now at its limit, but Org B hasn't created anything yet.
    b_created = await client.post(
        "/api/suppliers",
        json={"legal_name": "Acme B", "tax_id": "00000000000191", "jurisdiction": "BR"},
        headers=b_headers,
    )
    assert b_created.status_code == 201, b_created.text
