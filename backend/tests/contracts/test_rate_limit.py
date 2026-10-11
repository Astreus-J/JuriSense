"""#143: `POST /contracts/upload` dispatches AI extraction (CON-003) -- a real external
API call (the configured AI Gateway provider) plus a Celery task, the same external-call
shape the load test found unthrottled for Suppliers' recheck endpoint.
"""

import httpx

from app.core.config import get_settings
from tests.contracts.conftest import create_supplier, pdf_bytes_with_text, register_org_and_login


async def _upload(client: httpx.AsyncClient, headers: dict, supplier_id: str) -> httpx.Response:
    return await client.post(
        "/api/contracts/upload",
        files={"file": ("contract.pdf", pdf_bytes_with_text(), "application/pdf")},
        data={
            "supplier_id": supplier_id,
            "title": "Master Service Agreement",
            "contract_type": "msa",
        },
        headers=headers,
    )


async def test_upload_is_rate_limited_per_organization(client: httpx.AsyncClient) -> None:
    headers = await register_org_and_login(client, "rate-limit-upload@example.com")
    supplier = await create_supplier(client, headers, tax_id="00000000000191")
    budget = get_settings().external_call_rate_limit_max_requests

    for _ in range(budget):
        response = await _upload(client, headers, supplier["id"])
        assert response.status_code == 201, response.text

    limited = await _upload(client, headers, supplier["id"])
    assert limited.status_code == 429, limited.text
    assert int(limited.headers["retry-after"]) > 0
