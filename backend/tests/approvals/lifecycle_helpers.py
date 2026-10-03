"""Shared setup for the FEATURE-6.5 Decision-lifecycle and re-evaluation-retry tests. Plain
helpers, not tests: the test modules import these so the chain-building steps are written
once, the same way `tests/approvals/conftest.py` shares its own helpers."""

import uuid
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.approvals.application.sla_service import expire_stale_approval_requests
from app.approvals.infrastructure.models import ApprovalRequest, Decision
from app.evidence.infrastructure.repositories import AuditEventRepository
from app.identity.infrastructure.repositories import UserRepository
from app.policies.infrastructure.models import ComplianceReview
from tests.approvals.conftest import (
    ACTIVE_CNPJ_RESPONSE,
    create_supplier,
    create_user_and_login,
    register_org_and_login,
)
from tests.policies.test_compliance_review import (
    EVIDENCE_ENVELOPE,
    FIN_003_YAML,
    TAX_ID,
    _create_policy_with_rules,
    _upload_contract,
)


async def superseding_review_ids(
    db_session_factory: async_sessionmaker, decision_id: uuid.UUID
) -> set[uuid.UUID]:
    """Every ComplianceReview that is a re-evaluation of this Decision."""
    async with db_session_factory() as session:
        result = await session.execute(
            select(ComplianceReview.id).where(
                ComplianceReview.supersedes_decision_id == decision_id
            )
        )
        return set(result.scalars())


async def expire_pending_chain(
    db_session_factory: async_sessionmaker, review_id: uuid.UUID
) -> None:
    """Pushes every pending request of this review past the SLA and runs the real SLA-expiry
    sweep, so the chain ends `expired` exactly as production would end it."""
    async with db_session_factory() as session:
        requests = (
            (
                await session.execute(
                    select(ApprovalRequest).where(
                        ApprovalRequest.compliance_review_id == review_id,
                        ApprovalRequest.status == "pending",
                    )
                )
            )
            .scalars()
            .all()
        )
        for request in requests:
            request.requested_at = datetime.now(UTC) - timedelta(hours=72)
        await session.commit()
    async with db_session_factory() as session:
        await expire_stale_approval_requests(session)


async def pending_request_for(client: httpx.AsyncClient, headers: dict, review_id: str) -> dict:
    listed = await client.get(
        "/api/approvals/requests",
        params={"compliance_review_id": review_id},
        headers=headers,
    )
    [pending] = [r for r in listed.json() if r["status"] == "pending"]
    return pending


async def approve_pending_for(
    client: httpx.AsyncClient, approver_headers: dict, admin_headers: dict, review_id: str
) -> None:
    pending = await pending_request_for(client, admin_headers, review_id)
    approved = await client.post(
        f"/api/approvals/requests/{pending['id']}/approve",
        json={"justification": "approved in test"},
        headers=approver_headers,
    )
    assert approved.status_code == 200, approved.text


async def decision_row(db_session_factory: async_sessionmaker, decision_id: uuid.UUID) -> Decision:
    async with db_session_factory() as session:
        return await session.get(Decision, decision_id)


async def active_decisions_for_version(
    db_session_factory: async_sessionmaker, contract_version_id: uuid.UUID
) -> list[Decision]:
    async with db_session_factory() as session:
        result = await session.execute(
            select(Decision).where(
                Decision.contract_version_id == contract_version_id,
                Decision.lifecycle == "ACTIVE",
            )
        )
        return list(result.scalars())


async def audit_events(
    db_session_factory: async_sessionmaker, organization_id: uuid.UUID, event_type: str
) -> list:
    async with db_session_factory() as session:
        return await AuditEventRepository(session).list(
            organization_id=organization_id, event_type=event_type
        )


async def finance_review_chain(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    *,
    email: str,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
) -> dict:
    """An organization with one FIN-003 policy (REVIEW, legal approval) and a contract whose
    first review was approved by legal, leaving one ACTIVE APPROVE Decision. Returns the
    headers, ids, and that Decision's id for the test to build on."""
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
    await approve_pending_for(client, legal_headers, admin_headers, review["id"])

    organization_id = await _organization_id(db_session_factory, email)
    [decision] = [
        d
        for d in await _decisions_for_org(db_session_factory, organization_id)
        if d.status == "APPROVE"
    ]
    return {
        "admin_headers": admin_headers,
        "legal_headers": legal_headers,
        "contract_version_id": contract_version_id,
        "organization_id": organization_id,
        "decision_id": decision.id,
    }


async def _organization_id(db_session_factory: async_sessionmaker, email: str) -> uuid.UUID:
    async with db_session_factory() as session:
        user = await UserRepository(session).get_by_email(email)
        return user.organization_id


async def _decisions_for_org(
    db_session_factory: async_sessionmaker, organization_id: uuid.UUID
) -> list[Decision]:
    async with db_session_factory() as session:
        result = await session.execute(
            select(Decision).where(Decision.organization_id == organization_id)
        )
        return list(result.scalars())
