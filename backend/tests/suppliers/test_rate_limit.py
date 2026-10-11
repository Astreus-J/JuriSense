"""#143: `POST /suppliers` and `POST /suppliers/{id}/recheck` both trigger a real
SupplierCheck (CNPJ registry + sanctions calls, plus a Celery task) -- confirmed via load
test to be completely unthrottled before this. Both routes share one per-organization
budget (`external_call_rate_limit_max_requests`/`_window_seconds`, same `key_prefix`), since
they trigger the identical downstream work.
"""

import httpx

from app.core.config import get_settings
from tests.suppliers.conftest import register_org_and_login


async def _create_supplier(client: httpx.AsyncClient, headers: dict) -> httpx.Response:
    return await client.post(
        "/api/suppliers",
        json={"legal_name": "Banco do Brasil SA", "tax_id": "00000000000191", "jurisdiction": "BR"},
        headers=headers,
    )


async def test_recheck_is_rate_limited_per_organization(client: httpx.AsyncClient) -> None:
    headers = await register_org_and_login(client, "rate-limit-recheck@example.com")
    created = (await _create_supplier(client, headers)).json()  # counts as 1 hit
    budget = get_settings().external_call_rate_limit_max_requests

    for _ in range(budget - 1):  # the creation above already used one slot
        response = await client.post(f"/api/suppliers/{created['id']}/recheck", headers=headers)
        assert response.status_code == 202, response.text

    limited = await client.post(f"/api/suppliers/{created['id']}/recheck", headers=headers)
    assert limited.status_code == 429, limited.text
    assert int(limited.headers["retry-after"]) > 0


async def test_the_rate_limit_is_scoped_per_organization_not_global(
    client: httpx.AsyncClient,
) -> None:
    """Org A exhausting its budget must never affect Org B's own budget."""
    budget = get_settings().external_call_rate_limit_max_requests

    a_headers = await register_org_and_login(client, "rate-limit-org-a@example.com")
    a_created = (await _create_supplier(client, a_headers)).json()
    for _ in range(budget - 1):
        response = await client.post(f"/api/suppliers/{a_created['id']}/recheck", headers=a_headers)
        assert response.status_code == 202, response.text
    exhausted = await client.post(f"/api/suppliers/{a_created['id']}/recheck", headers=a_headers)
    assert exhausted.status_code == 429, exhausted.text

    b_headers = await register_org_and_login(client, "rate-limit-org-b@example.com")
    b_created = await _create_supplier(client, b_headers)
    assert b_created.status_code == 201, b_created.text
