"""CON-003/AI-001/AI-002/AI-003/BR-CON-003: AI structured extraction runs on
ContractVersion creation, populates extracted_data + Clause rows with provenance, and the
confidence gate routes the version to `analyzed` or `needs_confirmation`. All AI Gateway
HTTP calls are mocked (`mock_openrouter`) -- hermetic, per the EPIC-3 brief.
"""

import io

import httpx
import pypdf

from tests.contracts.conftest import (
    HIGH_CONFIDENCE_ENVELOPE,
    LOW_CONFIDENCE_ENVELOPE,
    create_supplier,
    register_org_and_login,
)


def _pdf_bytes() -> bytes:
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


async def _upload_and_refetch(client: httpx.AsyncClient, headers: dict, supplier_id: str) -> dict:
    """Uploads, then re-fetches the version via GET -- the upload response itself
    reflects the state at commit time (`extracted`, before the async extraction step
    runs), exactly like `POST /suppliers`'s response doesn't reflect its own
    just-enqueued `SupplierCheck` outcome either (see `tests/suppliers/test_supplier_check.py`,
    which always re-`GET`s after the inline fixture runs, for the same reason: two
    separate `AsyncSession` objects, each with its own identity map, even though the
    inline fixture runs "synchronously" from the test's point of view)."""
    uploaded = (
        await client.post(
            "/api/contracts/upload",
            files={"file": ("contract.pdf", _pdf_bytes(), "application/pdf")},
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


async def test_high_confidence_extraction_marks_analyzed_with_clauses(
    client: httpx.AsyncClient, mock_openrouter, run_contract_extraction_inline
) -> None:
    mock_openrouter(payload=HIGH_CONFIDENCE_ENVELOPE)
    headers = await register_org_and_login(client, "extract-high@example.com")
    supplier = await create_supplier(client, headers, tax_id="00000000000191")

    version = await _upload_and_refetch(client, headers, supplier["id"])
    assert version["status"] == "analyzed"
    # min confidence across all fields, which is processes_personal_data (0.9)
    assert version["extraction_confidence"] == 0.9
    assert version["extracted_data"]["fields"]["contract_type"]["value"] == "saas_subscription"

    clauses = (
        await client.get(
            f"/api/contracts/{version['contract_id']}/versions/{version['id']}/clauses",
            headers=headers,
        )
    ).json()
    assert len(clauses) == 1
    assert clauses[0]["clause_type"] == "liability"
    assert clauses[0]["page"] == 2
    assert clauses[0]["text_span"] == {"start": 0, "end": 10}


async def test_low_confidence_field_marks_needs_confirmation(
    client: httpx.AsyncClient, mock_openrouter, run_contract_extraction_inline
) -> None:
    mock_openrouter(payload=LOW_CONFIDENCE_ENVELOPE)
    headers = await register_org_and_login(client, "extract-low@example.com")
    supplier = await create_supplier(client, headers, tax_id="00000000000191")

    version = await _upload_and_refetch(client, headers, supplier["id"])
    assert version["status"] == "needs_confirmation"
    assert version["extraction_confidence"] == 0.4


async def test_all_providers_exhausted_marks_extraction_failed(
    client: httpx.AsyncClient, mock_openrouter, run_contract_extraction_inline
) -> None:
    mock_openrouter(status_code=429)
    headers = await register_org_and_login(client, "extract-fail@example.com")
    supplier = await create_supplier(client, headers, tax_id="00000000000191")

    version = await _upload_and_refetch(client, headers, supplier["id"])
    assert version["status"] == "extraction_failed"
    assert version["extraction_failure_reason"] is not None
