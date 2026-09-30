"""CON-003/AI-001/AI-002/AI-003/BR-CON-003: AI structured extraction runs on
ContractVersion creation, populates extracted_data + Clause rows with provenance, and the
confidence gate routes the version to `analyzed` or `needs_confirmation`. All AI Gateway
HTTP calls are mocked (`mock_openrouter`) -- hermetic, per the EPIC-3 brief.
"""

import io

import httpx
import pypdf

from app.core.config import get_settings
from tests.contracts.conftest import (
    HIGH_CONFIDENCE_ENVELOPE,
    LOW_CONFIDENCE_ENVELOPE,
    _envelope_with_min_confidence,
    create_supplier,
    pdf_bytes_with_text,
    register_org_and_login,
)


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


async def test_confidence_exactly_at_the_threshold_marks_analyzed(
    client: httpx.AsyncClient, mock_openrouter, run_contract_extraction_inline
) -> None:
    """BR-CON-003: "meeting the minimum confidence threshold" is `>=`, not `>` -- a
    field at exactly the threshold must pass, not be treated as below it."""
    threshold = get_settings().contract_extraction_confidence_threshold
    mock_openrouter(payload=_envelope_with_min_confidence(threshold))
    headers = await register_org_and_login(client, "extract-boundary-at@example.com")
    supplier = await create_supplier(client, headers, tax_id="00000000000191")

    version = await _upload_and_refetch(client, headers, supplier["id"])
    assert version["status"] == "analyzed"
    assert version["extraction_confidence"] == threshold


async def test_confidence_just_below_the_threshold_marks_needs_confirmation(
    client: httpx.AsyncClient, mock_openrouter, run_contract_extraction_inline
) -> None:
    threshold = get_settings().contract_extraction_confidence_threshold
    mock_openrouter(payload=_envelope_with_min_confidence(threshold - 0.01))
    headers = await register_org_and_login(client, "extract-boundary-below@example.com")
    supplier = await create_supplier(client, headers, tax_id="00000000000191")

    version = await _upload_and_refetch(client, headers, supplier["id"])
    assert version["status"] == "needs_confirmation"


async def test_blank_document_marks_extraction_failed(
    client: httpx.AsyncClient, mock_openrouter, run_contract_extraction_inline
) -> None:
    """QA review (2026-09-29): `text_extraction.py`'s own docstring already claimed an
    entirely-empty document (e.g. a scanned/image-only PDF -- OCR is a documented TBD)
    would fail fast as `document.processing_failed`, but nothing implemented it; a blank
    document silently proceeded to the AI Gateway with empty page content instead. Note
    `mock_openrouter` is still wired up here so a bug that regresses this check would
    surface as a wrong *status*, not a confusing "no mock configured" test failure.
    """
    mock_openrouter(payload=HIGH_CONFIDENCE_ENVELOPE)
    headers = await register_org_and_login(client, "extract-blank@example.com")
    supplier = await create_supplier(client, headers, tax_id="00000000000191")

    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=200, height=200)  # deliberately no content stream at all
    buf = io.BytesIO()
    writer.write(buf)

    uploaded = (
        await client.post(
            "/api/contracts/upload",
            files={"file": ("blank.pdf", buf.getvalue(), "application/pdf")},
            data={"supplier_id": supplier["id"], "title": "MSA", "contract_type": "msa"},
            headers=headers,
        )
    ).json()
    version = (
        await client.get(
            f"/api/contracts/{uploaded['contract_id']}/versions/{uploaded['id']}",
            headers=headers,
        )
    ).json()

    assert version["status"] == "extraction_failed"
    assert "no extractable text" in version["extraction_failure_reason"]


async def test_all_providers_exhausted_marks_extraction_failed(
    client: httpx.AsyncClient, mock_openrouter, run_contract_extraction_inline
) -> None:
    mock_openrouter(status_code=429)
    headers = await register_org_and_login(client, "extract-fail@example.com")
    supplier = await create_supplier(client, headers, tax_id="00000000000191")

    version = await _upload_and_refetch(client, headers, supplier["id"])
    assert version["status"] == "extraction_failed"
    # Security review (2026-09-29): the raw upstream response body (here, the mock's
    # literal "error" text) must never reach the API-exposed reason -- only the log.
    assert version["extraction_failure_reason"] == (
        "AI extraction failed after trying all configured providers/models"
    )
