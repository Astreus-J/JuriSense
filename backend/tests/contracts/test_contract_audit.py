"""FEATURE-7.2 / STORY-7.2.1: AuditEvents for document upload and processing, contract and
version creation, extraction outcomes, and human confirmation [AUD-001]."""

import io

import httpx
import pypdf
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.evidence.infrastructure.repositories import AuditEventRepository
from app.identity.infrastructure.repositories import UserRepository
from tests.contracts.conftest import (
    HIGH_CONFIDENCE_ENVELOPE,
    LOW_CONFIDENCE_ENVELOPE,
    create_supplier,
    pdf_bytes_with_text,
    register_org_and_login,
)

EMAIL = "audit-contracts@example.com"


async def _upload(
    client: httpx.AsyncClient,
    headers: dict,
    supplier_id: str,
    *,
    contract_id: str | None = None,
    content: bytes | None = None,
) -> dict:
    data = {"supplier_id": supplier_id}
    if contract_id is None:
        data.update({"title": "Master Service Agreement", "contract_type": "msa"})
    else:
        data["contract_id"] = contract_id
    response = await client.post(
        "/api/contracts/upload",
        files={"file": ("contract.pdf", content or pdf_bytes_with_text(), "application/pdf")},
        data=data,
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _events(db_session_factory: async_sessionmaker, event_type: str) -> list:
    async with db_session_factory() as session:
        return await AuditEventRepository(session).list(event_type=event_type)


async def _user(db_session_factory: async_sessionmaker):
    async with db_session_factory() as session:
        return await UserRepository(session).get_by_email(EMAIL)


async def test_upload_emits_document_uploaded_processed_contract_created_and_analysis_completed(
    client: httpx.AsyncClient,
    mock_openrouter,
    run_contract_extraction_inline,
    db_session_factory: async_sessionmaker,
) -> None:
    mock_openrouter(payload=HIGH_CONFIDENCE_ENVELOPE)
    headers = await register_org_and_login(client, EMAIL)
    supplier = await create_supplier(client, headers, tax_id="00000000000191")
    version = await _upload(client, headers, supplier["id"])
    admin = await _user(db_session_factory)

    [uploaded] = await _events(db_session_factory, "document.uploaded")
    [processed] = await _events(db_session_factory, "document.processed")
    [created] = await _events(db_session_factory, "contract.created")
    [completed] = await _events(db_session_factory, "contract.analysis_completed")
    for event in (uploaded, processed, created, completed):
        assert event.organization_id == admin.organization_id
    assert uploaded.actor_id == admin.id
    assert uploaded.payload["document_id"]
    assert created.payload["contract_id"] == version["contract_id"]
    assert completed.payload["contract_version_id"] == version["id"]
    assert await _events(db_session_factory, "contract.version_created") == []


async def test_reupload_emits_contract_version_created(
    client: httpx.AsyncClient,
    mock_openrouter,
    run_contract_extraction_inline,
    db_session_factory: async_sessionmaker,
) -> None:
    mock_openrouter(payload=HIGH_CONFIDENCE_ENVELOPE)
    headers = await register_org_and_login(client, EMAIL)
    supplier = await create_supplier(client, headers, tax_id="00000000000191")
    first = await _upload(client, headers, supplier["id"])
    second = await _upload(client, headers, supplier["id"], contract_id=first["contract_id"])

    [event] = await _events(db_session_factory, "contract.version_created")
    assert event.payload["contract_version_id"] == second["id"]
    assert event.payload["contract_id"] == first["contract_id"]
    assert len(await _events(db_session_factory, "contract.created")) == 1


async def test_low_confidence_extraction_emits_analysis_needs_confirmation(
    client: httpx.AsyncClient,
    mock_openrouter,
    run_contract_extraction_inline,
    db_session_factory: async_sessionmaker,
) -> None:
    mock_openrouter(payload=LOW_CONFIDENCE_ENVELOPE)
    headers = await register_org_and_login(client, EMAIL)
    supplier = await create_supplier(client, headers, tax_id="00000000000191")
    version = await _upload(client, headers, supplier["id"])

    [event] = await _events(db_session_factory, "contract.analysis_needs_confirmation")
    assert event.payload["contract_version_id"] == version["id"]
    assert await _events(db_session_factory, "contract.analysis_completed") == []


async def test_human_confirmation_emits_version_confirmed_and_analysis_completed(
    client: httpx.AsyncClient,
    mock_openrouter,
    run_contract_extraction_inline,
    db_session_factory: async_sessionmaker,
) -> None:
    mock_openrouter(payload=LOW_CONFIDENCE_ENVELOPE)
    headers = await register_org_and_login(client, EMAIL)
    supplier = await create_supplier(client, headers, tax_id="00000000000191")
    version = await _upload(client, headers, supplier["id"])

    confirmed = await client.post(
        f"/api/contracts/{version['contract_id']}/versions/{version['id']}/confirm",
        json={"corrections": {}},
        headers=headers,
    )
    assert confirmed.status_code == 200, confirmed.text

    [confirmed_event] = await _events(db_session_factory, "contract.version_confirmed")
    [completed] = await _events(db_session_factory, "contract.analysis_completed")
    assert confirmed_event.actor_id == (await _user(db_session_factory)).id
    assert confirmed_event.payload["contract_version_id"] == version["id"]
    assert confirmed_event.payload["corrected_fields"] == []
    assert completed.payload["via_human_confirmation"] is True


async def test_unparseable_document_emits_document_processing_failed(
    client: httpx.AsyncClient,
    run_contract_extraction_inline,
    db_session_factory: async_sessionmaker,
) -> None:
    """A PDF with no extractable text fails parsing before any AI call, so no mock is needed."""
    buf = io.BytesIO()
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.write(buf)
    headers = await register_org_and_login(client, EMAIL)
    supplier = await create_supplier(client, headers, tax_id="00000000000191")
    version = await _upload(client, headers, supplier["id"], content=buf.getvalue())

    [event] = await _events(db_session_factory, "document.processing_failed")
    assert event.actor_id is None
    assert event.payload["contract_version_id"] == version["id"]
    assert event.payload["reason"]
