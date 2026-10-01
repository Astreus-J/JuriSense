"""FEATURE-6.3/STORY-6.3.1 (DEC-001, BR-DEC-001): an `APPROVE` or `BLOCK` aggregate
`ComplianceReview` outcome gets its `Decision` created synchronously, inside the SAME
`trigger_review` call -- never deferred, since neither outcome needs a human approval
step. Tested at the integration level against the real `POST /api/compliance/reviews`
endpoint, per this epic's own testing-expectations note.
"""

import uuid

import httpx
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.approvals.infrastructure.repositories import DecisionRepository
from app.identity.infrastructure.repositories import UserRepository
from tests.approvals.conftest import (
    ACTIVE_CNPJ_RESPONSE,
    create_supplier,
    register_org_and_login,
)
from tests.policies.test_compliance_review import (
    EVIDENCE_ENVELOPE,
    FIN_003_YAML,
    SANC_001_YAML,
    TAX_ID,
    _create_policy_with_rules,
    _upload_contract,
)


async def _get_decision_for_review(
    db_session_factory: async_sessionmaker, *, organization_id, compliance_review_id
):
    """`compliance_review_id` is accepted as either a `str` (as it comes back from a JSON
    response body) or a `uuid.UUID` -- normalized here once, since `sa.Uuid()` columns'
    bind-parameter processor requires an actual `uuid.UUID` instance, not a plain `str`."""
    async with db_session_factory() as session:
        return await DecisionRepository(session).get_by_review(
            uuid.UUID(str(compliance_review_id)), organization_id
        )


async def test_block_aggregate_outcome_creates_decision_immediately(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
) -> None:
    mock_cnpj_registry(data=ACTIVE_CNPJ_RESPONSE)
    await seed_sanctions_index(hit_document=TAX_ID)
    mock_openrouter(payload=EVIDENCE_ENVELOPE)

    headers = await register_org_and_login(client, "block-decision@example.com")
    supplier = await create_supplier(client, headers, tax_id=TAX_ID)
    contract_version_id = await _upload_contract(client, headers, supplier["id"])
    await _create_policy_with_rules(
        client, headers, name="Vendor Policy", rule_yamls=[SANC_001_YAML]
    )

    response = await client.post(
        "/api/compliance/reviews",
        json={"contract_version_id": contract_version_id},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    review = response.json()
    assert review["status"] == "BLOCK"

    async with db_session_factory() as session:
        admin = await UserRepository(session).get_by_email("block-decision@example.com")
        organization_id = admin.organization_id

    decision = await _get_decision_for_review(
        db_session_factory, organization_id=organization_id, compliance_review_id=review["id"]
    )
    assert decision is not None
    assert decision.status == "BLOCK"
    assert decision.overridden is False
    assert decision.valid_until is not None

    # No ApprovalRequest exists for a BLOCK outcome -- it is "not reviewable through this
    # workflow" (docs/03-domain/approvals.md).
    requests = await client.get(
        "/api/approvals/requests", params={"compliance_review_id": review["id"]}, headers=headers
    )
    assert requests.status_code == 200, requests.text
    assert requests.json() == []

    # The read API surface too.
    get_decision = await client.get(f"/api/decisions/{decision.id}", headers=headers)
    assert get_decision.status_code == 200, get_decision.text
    assert get_decision.json()["status"] == "BLOCK"


async def test_approve_aggregate_outcome_creates_decision_immediately(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    run_contract_extraction_inline,
) -> None:
    """Zero applicable/triggered rules -> aggregate APPROVE (ADR-010 §2's "else APPROVE")
    -- also gets its Decision created synchronously."""
    mock_openrouter(payload=EVIDENCE_ENVELOPE)
    headers = await register_org_and_login(client, "approve-decision@example.com")
    supplier = await create_supplier(client, headers, tax_id=TAX_ID)
    contract_version_id = await _upload_contract(client, headers, supplier["id"])
    # FIN_003 needs a value well above its threshold to differ from the supplied
    # evidence's amount being used -- using zero rules keeps this test's intent crystal
    # clear: no policy at all -> trivially APPROVE.

    response = await client.post(
        "/api/compliance/reviews",
        json={"contract_version_id": contract_version_id},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    review = response.json()
    assert review["status"] == "APPROVE"

    async with db_session_factory() as session:
        admin = await UserRepository(session).get_by_email("approve-decision@example.com")
        organization_id = admin.organization_id

    decision = await _get_decision_for_review(
        db_session_factory, organization_id=organization_id, compliance_review_id=review["id"]
    )
    assert decision is not None
    assert decision.status == "APPROVE"


async def test_review_aggregate_outcome_has_no_decision_until_chain_resolves(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
) -> None:
    """The critical timing nuance: a REVIEW aggregate outcome gets NO Decision row at all
    while its approval chain is still pending -- not a placeholder, genuinely absent."""
    mock_cnpj_registry(data=ACTIVE_CNPJ_RESPONSE)
    await seed_sanctions_index(hit_document=TAX_ID)
    mock_openrouter(payload=EVIDENCE_ENVELOPE)

    headers = await register_org_and_login(client, "pending-decision@example.com")
    supplier = await create_supplier(client, headers, tax_id=TAX_ID)
    contract_version_id = await _upload_contract(client, headers, supplier["id"])
    await _create_policy_with_rules(
        client, headers, name="Vendor Policy", rule_yamls=[FIN_003_YAML]
    )

    response = await client.post(
        "/api/compliance/reviews",
        json={"contract_version_id": contract_version_id},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    review = response.json()
    assert review["status"] == "REVIEW"

    async with db_session_factory() as session:
        admin = await UserRepository(session).get_by_email("pending-decision@example.com")
        organization_id = admin.organization_id

    decision = await _get_decision_for_review(
        db_session_factory, organization_id=organization_id, compliance_review_id=review["id"]
    )
    assert decision is None
