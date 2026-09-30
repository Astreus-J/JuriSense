"""CON-001/CON-002/BR-CON-001/BR-CON-002: contract document upload, and re-upload
against an existing Contract creating a new, immutable ContractVersion (never mutating a
prior one -- tested explicitly per the EPIC-3 brief).
"""

import httpx

from app.contracts.infrastructure.repositories import ContractVersionRepository
from tests.contracts.conftest import (
    HIGH_CONFIDENCE_ENVELOPE,
    create_supplier,
    pdf_bytes_with_text,
    register_org_and_login,
)


async def test_upload_creates_new_contract_and_first_version(client: httpx.AsyncClient) -> None:
    headers = await register_org_and_login(client, "upload1@example.com")
    supplier = await create_supplier(client, headers, tax_id="00000000000191")

    response = await client.post(
        "/api/contracts/upload",
        files={"file": ("contract.pdf", pdf_bytes_with_text(), "application/pdf")},
        data={
            "supplier_id": supplier["id"],
            "title": "Master Service Agreement",
            "contract_type": "msa",
        },
        headers=headers,
    )
    assert response.status_code == 201
    version = response.json()
    assert version["version_number"] == 1
    assert version["status"] == "extracted"  # extraction is stubbed (no-op) by default

    contracts = (await client.get("/api/contracts", headers=headers)).json()
    assert len(contracts) == 1
    assert contracts[0]["supplier_id"] == supplier["id"]
    assert contracts[0]["status"] == "draft"


async def test_upload_without_contract_id_requires_title_and_type(
    client: httpx.AsyncClient,
) -> None:
    headers = await register_org_and_login(client, "upload2@example.com")
    supplier = await create_supplier(client, headers, tax_id="00000000000191")

    response = await client.post(
        "/api/contracts/upload",
        files={"file": ("contract.pdf", pdf_bytes_with_text(), "application/pdf")},
        data={"supplier_id": supplier["id"]},
        headers=headers,
    )
    assert response.status_code == 422


async def test_reupload_against_existing_contract_creates_new_version(
    client: httpx.AsyncClient, mock_openrouter, run_contract_extraction_inline
) -> None:
    mock_openrouter(payload=HIGH_CONFIDENCE_ENVELOPE)
    headers = await register_org_and_login(client, "reupload@example.com")
    supplier = await create_supplier(client, headers, tax_id="00000000000191")

    first = (
        await client.post(
            "/api/contracts/upload",
            files={"file": ("v1.pdf", pdf_bytes_with_text(), "application/pdf")},
            data={
                "supplier_id": supplier["id"],
                "title": "Renewal Contract",
                "contract_type": "msa",
            },
            headers=headers,
        )
    ).json()
    contract_id = first["contract_id"]
    assert first["version_number"] == 1

    # Re-fetch: the upload response itself reflects pre-extraction state (`extracted`),
    # since extraction is dispatched asynchronously -- same reasoning as
    # `tests/suppliers/test_supplier_check.py` always re-`GET`ing after its own inline
    # fixture rather than trusting the creation response's own body.
    first = (
        await client.get(f"/api/contracts/{contract_id}/versions/{first['id']}", headers=headers)
    ).json()
    assert first["status"] == "analyzed"
    first_extracted_data = first["extracted_data"]

    second = (
        await client.post(
            "/api/contracts/upload",
            files={"file": ("v2.pdf", pdf_bytes_with_text(), "application/pdf")},
            data={"supplier_id": supplier["id"], "contract_id": contract_id},
            headers=headers,
        )
    ).json()
    assert second["version_number"] == 2
    assert second["contract_id"] == contract_id

    # The first version's row must be entirely unchanged after the second upload.
    refetched_first = (
        await client.get(f"/api/contracts/{contract_id}/versions/{first['id']}", headers=headers)
    ).json()
    assert refetched_first["extracted_data"] == first_extracted_data
    assert refetched_first["version_number"] == 1

    versions = (await client.get(f"/api/contracts/{contract_id}/versions", headers=headers)).json()
    assert len(versions) == 2
    assert {v["version_number"] for v in versions} == {1, 2}


async def test_reupload_with_different_supplier_rejected(client: httpx.AsyncClient) -> None:
    headers = await register_org_and_login(client, "mismatch@example.com")
    supplier_a = await create_supplier(client, headers, tax_id="00000000000191")
    supplier_b = await create_supplier(client, headers, tax_id="11444777000161")

    first = (
        await client.post(
            "/api/contracts/upload",
            files={"file": ("v1.pdf", pdf_bytes_with_text(), "application/pdf")},
            data={"supplier_id": supplier_a["id"], "title": "MSA", "contract_type": "msa"},
            headers=headers,
        )
    ).json()

    response = await client.post(
        "/api/contracts/upload",
        files={"file": ("v2.pdf", pdf_bytes_with_text(), "application/pdf")},
        data={"supplier_id": supplier_b["id"], "contract_id": first["contract_id"]},
        headers=headers,
    )
    assert response.status_code == 409


async def test_upload_rejects_type_spoofed_file(client: httpx.AsyncClient) -> None:
    headers = await register_org_and_login(client, "spoof@example.com")
    supplier = await create_supplier(client, headers, tax_id="00000000000191")

    response = await client.post(
        "/api/contracts/upload",
        files={"file": ("contract.pdf", b"MZ" + b"\x90" * 50, "application/pdf")},
        data={"supplier_id": supplier["id"], "title": "MSA", "contract_type": "msa"},
        headers=headers,
    )
    assert response.status_code == 422


async def test_new_contract_rejects_another_organizations_supplier_id(
    client: httpx.AsyncClient,
) -> None:
    """Security review (2026-09-29): confirmed live that a new Contract previously
    accepted any real supplier_id regardless of which organization it belonged to --
    the FK constraint only caught a *nonexistent* one. Org B's supplier_id must be
    rejected when Org A tries to create a contract against it, even though it's a real,
    existing supplier row."""
    headers_a = await register_org_and_login(client, "idor-a@example.com")
    headers_b = await register_org_and_login(client, "idor-b@example.com")
    supplier_b = await create_supplier(client, headers_b, tax_id="00000000000191")

    response = await client.post(
        "/api/contracts/upload",
        files={"file": ("contract.pdf", pdf_bytes_with_text(), "application/pdf")},
        data={
            "supplier_id": supplier_b["id"],
            "title": "Cross-tenant attempt",
            "contract_type": "msa",
        },
        headers=headers_a,
    )
    assert response.status_code == 422

    # Confirm no contract was actually created for Org A against Org B's supplier.
    contracts_a = (await client.get("/api/contracts", headers=headers_a)).json()
    assert contracts_a == []


async def test_concurrent_reuploads_yield_one_success_and_one_clean_conflict(
    client: httpx.AsyncClient, monkeypatch
) -> None:
    """QA review (2026-09-29): the ContractVersion flush previously had no
    IntegrityError handler (unlike the equivalent handler on Contract creation), so the
    losing side of a concurrent re-upload race -- two requests computing the same "next"
    version_number before either commits -- surfaced as an unhandled 500 instead of a
    clean 409.

    True concurrency can't be reproduced hermetically here: the test DB is SQLite over a
    single shared `StaticPool` connection, which doesn't support two genuinely
    concurrent transactions the way the real asyncpg/Postgres pool does. Instead this
    deterministically forces the exact collision a race would produce, by making
    `get_next_version_number` return an already-used number on the second call -- the
    same effect two simultaneous requests reading a stale "next" value would have.
    """
    headers = await register_org_and_login(client, "race@example.com")
    supplier = await create_supplier(client, headers, tax_id="00000000000191")

    first = (
        await client.post(
            "/api/contracts/upload",
            files={"file": ("v1.pdf", pdf_bytes_with_text(), "application/pdf")},
            data={"supplier_id": supplier["id"], "title": "MSA", "contract_type": "msa"},
            headers=headers,
        )
    ).json()
    contract_id = first["contract_id"]

    real_get_next = ContractVersionRepository.get_next_version_number
    call_count = {"n": 0}

    async def _stale_get_next(self, contract_id):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return await real_get_next(self, contract_id)
        # Second call: pretend it computed "2" before the first re-upload committed --
        # exactly what a genuine race would produce.
        return 2

    monkeypatch.setattr(ContractVersionRepository, "get_next_version_number", _stale_get_next)

    first_response = await client.post(
        "/api/contracts/upload",
        files={"file": ("v2a.pdf", pdf_bytes_with_text(), "application/pdf")},
        data={"supplier_id": supplier["id"], "contract_id": contract_id},
        headers=headers,
    )
    second_response = await client.post(
        "/api/contracts/upload",
        files={"file": ("v2b.pdf", pdf_bytes_with_text(), "application/pdf")},
        data={"supplier_id": supplier["id"], "contract_id": contract_id},
        headers=headers,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409  # not 500, and not a silent duplicate


async def test_cross_tenant_contract_access_denied(client: httpx.AsyncClient) -> None:
    headers_a = await register_org_and_login(client, "tenant-a@example.com")
    supplier_a = await create_supplier(client, headers_a, tax_id="00000000000191")
    version = (
        await client.post(
            "/api/contracts/upload",
            files={"file": ("v1.pdf", pdf_bytes_with_text(), "application/pdf")},
            data={"supplier_id": supplier_a["id"], "title": "MSA", "contract_type": "msa"},
            headers=headers_a,
        )
    ).json()

    headers_b = await register_org_and_login(client, "tenant-b@example.com")
    response = await client.get(f"/api/contracts/{version['contract_id']}", headers=headers_b)
    assert response.status_code == 404
