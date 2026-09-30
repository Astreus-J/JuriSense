"""CON-005/BR-CON-003: human confirmation unblocks a `needs_confirmation` ContractVersion
to `analyzed`."""

import httpx

from tests.contracts.conftest import (
    LOW_CONFIDENCE_ENVELOPE,
    create_supplier,
    pdf_bytes_with_text,
    register_org_and_login,
)


async def _upload_and_refetch(client: httpx.AsyncClient, headers: dict, supplier_id: str) -> dict:
    """See `tests/contracts/test_extraction_pipeline.py::_upload_and_refetch`'s docstring
    for why a follow-up GET (not the upload response itself) is used to observe the
    post-extraction status."""
    uploaded = (
        await client.post(
            "/api/contracts/upload",
            files={"file": ("contract.pdf", pdf_bytes_with_text(), "application/pdf")},
            data={"supplier_id": supplier_id, "title": "MSA", "contract_type": "msa"},
            headers=headers,
        )
    ).json()
    return (
        await client.get(
            f"/api/contracts/{uploaded['contract_id']}/versions/{uploaded['id']}",
            headers=headers,
        )
    ).json()


async def test_confirm_as_is_marks_analyzed_without_changing_value(
    client: httpx.AsyncClient, mock_openrouter, run_contract_extraction_inline
) -> None:
    mock_openrouter(payload=LOW_CONFIDENCE_ENVELOPE)
    headers = await register_org_and_login(client, "confirm1@example.com")
    supplier = await create_supplier(client, headers, tax_id="00000000000191")
    version = await _upload_and_refetch(client, headers, supplier["id"])
    assert version["status"] == "needs_confirmation"

    response = await client.post(
        f"/api/contracts/{version['contract_id']}/versions/{version['id']}/confirm",
        json={"corrections": {}},
        headers=headers,
    )
    assert response.status_code == 200
    confirmed = response.json()
    assert confirmed["status"] == "analyzed"
    liability_type = confirmed["extracted_data"]["fields"]["liability"]["type"]
    assert liability_type["value"] == "unlimited"  # unchanged, confirmed as-is
    assert liability_type["human_confirmed"] is True
    assert liability_type["confidence"] == 0.4  # original AI confidence preserved


async def test_confirm_with_correction_applies_new_value(
    client: httpx.AsyncClient, mock_openrouter, run_contract_extraction_inline
) -> None:
    mock_openrouter(payload=LOW_CONFIDENCE_ENVELOPE)
    headers = await register_org_and_login(client, "confirm2@example.com")
    supplier = await create_supplier(client, headers, tax_id="00000000000191")
    version = await _upload_and_refetch(client, headers, supplier["id"])

    response = await client.post(
        f"/api/contracts/{version['contract_id']}/versions/{version['id']}/confirm",
        json={"corrections": {"liability.type": "capped"}},
        headers=headers,
    )
    assert response.status_code == 200
    confirmed = response.json()
    liability_type = confirmed["extracted_data"]["fields"]["liability"]["type"]
    assert liability_type["value"] == "capped"
    assert liability_type["human_confirmed"] is True
    assert liability_type["human_corrected"] is True


async def test_confirm_already_analyzed_version_rejected(
    client: httpx.AsyncClient, mock_openrouter, run_contract_extraction_inline
) -> None:
    from tests.contracts.conftest import HIGH_CONFIDENCE_ENVELOPE

    mock_openrouter(payload=HIGH_CONFIDENCE_ENVELOPE)
    headers = await register_org_and_login(client, "confirm3@example.com")
    supplier = await create_supplier(client, headers, tax_id="00000000000191")
    version = await _upload_and_refetch(client, headers, supplier["id"])
    assert version["status"] == "analyzed"

    response = await client.post(
        f"/api/contracts/{version['contract_id']}/versions/{version['id']}/confirm",
        json={"corrections": {}},
        headers=headers,
    )
    assert response.status_code == 409
