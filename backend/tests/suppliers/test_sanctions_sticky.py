"""STORY-2.8 / SUP-004 / BR-SUP-004: a sanctions hit is a non-silent blocking signal that
must persist as `true` across profile replacement until an explicit override/exception
clears it — which is EPIC-4 scope, not this one. This test proves the negative: a routine
re-check that finds no fresh hit must never silently clear a previously recorded flag.
"""

import httpx

from tests.suppliers.conftest import ACTIVE_CNPJ_RESPONSE, register_org_and_login

TAX_ID = "00000000000191"


async def test_sanctions_flag_stays_true_after_a_clean_recheck(
    client: httpx.AsyncClient,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_supplier_checks_inline,
) -> None:
    mock_cnpj_registry(data=ACTIVE_CNPJ_RESPONSE)
    await seed_sanctions_index(hit_document=TAX_ID)
    headers = await register_org_and_login(client, "sticky-sanctions@example.com")

    created = (
        await client.post(
            "/api/suppliers",
            json={"legal_name": "Banco do Brasil SA", "tax_id": TAX_ID, "jurisdiction": "BR"},
            headers=headers,
        )
    ).json()
    supplier_id = created["id"]

    first_history = (
        await client.get(f"/api/suppliers/{supplier_id}/checks", headers=headers)
    ).json()
    assert first_history[0]["status"] == "completed"
    first_hits = first_history[0]["raw_results"]["sanctions"]["data"]["hits"]
    assert len(first_hits) == 1

    # The sanctions-hit supplier cannot be approved (BR-SUP-003/BR-SUP-004).
    blocked = await client.patch(
        f"/api/suppliers/{supplier_id}/status", json={"status": "approved"}, headers=headers
    )
    assert blocked.status_code == 409

    # Second check: the sanctions list no longer carries the hit (no fresh clearance
    # signal — that requires an explicit override/exception record, EPIC-4 scope).
    await seed_sanctions_index()
    recheck = await client.post(f"/api/suppliers/{supplier_id}/recheck", headers=headers)
    assert recheck.status_code == 202
    second_history = (
        await client.get(f"/api/suppliers/{supplier_id}/checks", headers=headers)
    ).json()
    assert len(second_history) == 2
    second_hits = second_history[0]["raw_results"]["sanctions"]["data"]["hits"]
    assert second_hits == []  # this check itself found nothing

    # Yet the flag must still block approval — it was never explicitly cleared.
    still_blocked = await client.patch(
        f"/api/suppliers/{supplier_id}/status", json={"status": "approved"}, headers=headers
    )
    assert still_blocked.status_code == 409
