"""FEATURE-7.2 / STORY-7.2.1: AuditEvents for a human approval step being requested, approved,
and rejected [AUD-001]. Each test drives the real REVIEW -> approval chain, not a fixture row.
"""

import httpx
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.evidence.infrastructure.repositories import AuditEventRepository
from app.identity.infrastructure.repositories import UserRepository
from tests.approvals.conftest import (
    ACTIVE_CNPJ_RESPONSE,
    create_supplier,
    create_user_and_login,
    register_org_and_login,
)
from tests.approvals.lifecycle_helpers import pending_request_for
from tests.policies.test_compliance_review import (
    EVIDENCE_ENVELOPE,
    FIN_003_YAML,
    TAX_ID,
    _create_policy_with_rules,
    _upload_contract,
)


async def _events(db_session_factory: async_sessionmaker, event_type: str) -> list:
    async with db_session_factory() as session:
        return await AuditEventRepository(session).list(event_type=event_type)


async def _user_id(db_session_factory: async_sessionmaker, email: str):
    async with db_session_factory() as session:
        return (await UserRepository(session).get_by_email(email)).id


async def _review_awaiting_legal(
    client: httpx.AsyncClient,
    *,
    email: str,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
) -> tuple[dict, dict, str]:
    mock_cnpj_registry(data=ACTIVE_CNPJ_RESPONSE)
    await seed_sanctions_index(hit_document=TAX_ID)
    mock_openrouter(payload=EVIDENCE_ENVELOPE)
    admin_headers = await register_org_and_login(client, email)
    legal_headers = await create_user_and_login(
        client, admin_headers, email=f"legal-{email}", role="legal"
    )
    supplier = await create_supplier(client, admin_headers, tax_id=TAX_ID)
    contract_version_id = await _upload_contract(client, admin_headers, supplier["id"])
    await _create_policy_with_rules(
        client, admin_headers, name="Vendor Policy", rule_yamls=[FIN_003_YAML]
    )
    review = (
        await client.post(
            "/api/compliance/reviews",
            json={"contract_version_id": contract_version_id},
            headers=admin_headers,
        )
    ).json()
    assert review["status"] == "REVIEW"
    return admin_headers, legal_headers, review["id"]


async def test_review_requiring_approval_emits_approval_requested(
    client: httpx.AsyncClient,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
    db_session_factory: async_sessionmaker,
) -> None:
    admin_headers, _, review_id = await _review_awaiting_legal(
        client,
        email="audit-approval-requested@example.com",
        mock_openrouter=mock_openrouter,
        mock_cnpj_registry=mock_cnpj_registry,
        seed_sanctions_index=seed_sanctions_index,
        run_contract_extraction_inline=run_contract_extraction_inline,
        run_supplier_checks_inline=run_supplier_checks_inline,
    )
    pending = await pending_request_for(client, admin_headers, review_id)

    [event] = await _events(db_session_factory, "approval.requested")
    assert event.payload["approval_request_id"] == pending["id"]
    assert event.payload["compliance_review_id"] == review_id
    assert event.payload["approver_role"] == "legal"
    assert event.payload["step_number"] == 1


async def test_approving_a_request_emits_approval_approved_with_the_approver(
    client: httpx.AsyncClient,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
    db_session_factory: async_sessionmaker,
) -> None:
    email = "audit-approval-approved@example.com"
    admin_headers, legal_headers, review_id = await _review_awaiting_legal(
        client,
        email=email,
        mock_openrouter=mock_openrouter,
        mock_cnpj_registry=mock_cnpj_registry,
        seed_sanctions_index=seed_sanctions_index,
        run_contract_extraction_inline=run_contract_extraction_inline,
        run_supplier_checks_inline=run_supplier_checks_inline,
    )
    pending = await pending_request_for(client, admin_headers, review_id)

    approved = await client.post(
        f"/api/approvals/requests/{pending['id']}/approve",
        json={"justification": "approved in audit test"},
        headers=legal_headers,
    )
    assert approved.status_code == 200, approved.text

    [event] = await _events(db_session_factory, "approval.approved")
    assert event.actor_id == await _user_id(db_session_factory, f"legal-{email}")
    assert event.payload["approval_request_id"] == pending["id"]
    assert event.payload["approved_by"] == str(event.actor_id)


async def test_rejecting_a_request_emits_approval_rejected_with_the_rejecter(
    client: httpx.AsyncClient,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
    db_session_factory: async_sessionmaker,
) -> None:
    email = "audit-approval-rejected@example.com"
    admin_headers, legal_headers, review_id = await _review_awaiting_legal(
        client,
        email=email,
        mock_openrouter=mock_openrouter,
        mock_cnpj_registry=mock_cnpj_registry,
        seed_sanctions_index=seed_sanctions_index,
        run_contract_extraction_inline=run_contract_extraction_inline,
        run_supplier_checks_inline=run_supplier_checks_inline,
    )
    pending = await pending_request_for(client, admin_headers, review_id)

    rejected = await client.post(
        f"/api/approvals/requests/{pending['id']}/reject",
        json={"justification": "Terms need renegotiation"},
        headers=legal_headers,
    )
    assert rejected.status_code == 200, rejected.text

    [event] = await _events(db_session_factory, "approval.rejected")
    assert event.actor_id == await _user_id(db_session_factory, f"legal-{email}")
    assert event.payload["approval_request_id"] == pending["id"]
    assert event.payload["rejected_by"] == str(event.actor_id)
