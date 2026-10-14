"""Security audit (2026-10-12): per-organization resource-exhaustion backstop on new
Contracts -- unbounded creation is also unbounded cost (every uploaded version triggers
a real AI extraction call), the same gap #180 closed for Policies/PolicyVersions/Rules.
"""

import httpx
import pytest

from app.core.config import get_settings
from tests.contracts.conftest import create_supplier, pdf_bytes_with_text, register_org_and_login


async def _upload_new_contract(
    client: httpx.AsyncClient, headers: dict, supplier_id: str, *, title: str
) -> httpx.Response:
    return await client.post(
        "/api/contracts/upload",
        files={"file": ("contract.pdf", pdf_bytes_with_text(), "application/pdf")},
        data={"supplier_id": supplier_id, "title": title, "contract_type": "msa"},
        headers=headers,
    )


async def test_contract_creation_is_refused_once_the_organization_limit_is_reached(
    client: httpx.AsyncClient, mock_openrouter, monkeypatch: pytest.MonkeyPatch
) -> None:
    mock_openrouter(payload={"fields": {}, "clauses": []})
    monkeypatch.setattr(get_settings(), "max_contracts_per_organization", 1)
    headers = await register_org_and_login(client, "contract-limit@example.com")
    supplier = await create_supplier(client, headers, tax_id="00000000000191")

    first = await _upload_new_contract(client, headers, supplier["id"], title="MSA A")
    assert first.status_code == 201, first.text

    second = await _upload_new_contract(client, headers, supplier["id"], title="MSA B")
    assert second.status_code == 403, second.text
    assert "limit" in second.json()["detail"].lower()


async def test_contract_creation_is_scoped_per_organization_not_global(
    client: httpx.AsyncClient, mock_openrouter, monkeypatch: pytest.MonkeyPatch
) -> None:
    mock_openrouter(payload={"fields": {}, "clauses": []})
    monkeypatch.setattr(get_settings(), "max_contracts_per_organization", 1)

    a_headers = await register_org_and_login(client, "contract-limit-org-a@example.com")
    a_supplier = await create_supplier(client, a_headers, tax_id="00000000000191")
    a_created = await _upload_new_contract(client, a_headers, a_supplier["id"], title="MSA A")
    assert a_created.status_code == 201, a_created.text

    # Org A is now at its limit, but Org B hasn't created anything yet.
    b_headers = await register_org_and_login(client, "contract-limit-org-b@example.com")
    b_supplier = await create_supplier(client, b_headers, tax_id="00000000000191")
    b_created = await _upload_new_contract(client, b_headers, b_supplier["id"], title="MSA B")
    assert b_created.status_code == 201, b_created.text
