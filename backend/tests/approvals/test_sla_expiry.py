"""FEATURE-6.2/STORY-6.2.3 (BR-APR-003): SLA expiry of stale `pending` `ApprovalRequest`s.

Mirrors this codebase's existing pattern for testing a time-based Celery task (see
`tests/integrations/test_tasks.py`-style direct-function-call tests for the sanctions
refresh task): calls `sla_service.expire_stale_approval_requests` directly against the
test database, with a manipulated `requested_at`, rather than actually sleeping or
invoking Celery/the broker.
"""

import uuid
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.approvals.application.sla_service import expire_stale_approval_requests
from app.approvals.infrastructure.models import ApprovalRequest
from app.approvals.infrastructure.repositories import DecisionRepository
from app.evidence.infrastructure.repositories import AuditEventRepository
from app.identity.infrastructure.repositories import UserRepository
from tests.approvals.conftest import (
    ACTIVE_CNPJ_RESPONSE,
    create_supplier,
    register_org_and_login,
)
from tests.policies.test_compliance_review import (
    EVIDENCE_ENVELOPE,
    FIN_003_YAML,
    TAX_ID,
    _create_policy_with_rules,
    _upload_contract,
)


async def _review_with_pending_request(
    client: httpx.AsyncClient, headers: dict
) -> dict:
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
    return response.json()


async def test_pending_request_past_the_sla_is_expired_and_emits_an_audit_event(
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

    headers = await register_org_and_login(client, "sla-expired@example.com")
    review = await _review_with_pending_request(client, headers)
    request_id = (
        await client.get(
            "/api/approvals/requests",
            params={"compliance_review_id": review["id"]},
            headers=headers,
        )
    ).json()[0]["id"]
    request_uuid = uuid.UUID(request_id)

    # Default SLA is 48h (settings.approval_request_sla_hours) -- push requested_at well
    # past it.
    async with db_session_factory() as session:
        request = await session.get(ApprovalRequest, request_uuid)
        request.requested_at = datetime.now(UTC) - timedelta(hours=72)
        await session.commit()

    async with db_session_factory() as session:
        expired_count = await expire_stale_approval_requests(session)
    assert expired_count == 1

    async with db_session_factory() as session:
        request = await session.get(ApprovalRequest, request_uuid)
        assert request.status == "expired"

        admin = await UserRepository(session).get_by_email("sla-expired@example.com")
        expiry_events = await AuditEventRepository(session).list(
            organization_id=admin.organization_id, event_type="approval.expired"
        )
        assert len(expiry_events) == 1
        assert expiry_events[0].payload["approval_request_id"] == str(request_id)
        assert expiry_events[0].actor_id is None  # system-initiated, no human actor

        # No Decision is ever created for an expired review -- it blocks the review from
        # reaching one until an admin intervenes (docs/03-domain/approvals.md).
        decision = await DecisionRepository(session).get_by_review(
            uuid.UUID(review["id"]), admin.organization_id
        )
    assert decision is None

    detail = await client.get(f"/api/approvals/requests/{request_id}", headers=headers)
    assert detail.json()["status"] == "expired"


async def test_pending_request_within_the_sla_is_left_untouched(
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

    headers = await register_org_and_login(client, "sla-fresh@example.com")
    review = await _review_with_pending_request(client, headers)
    request_id = (
        await client.get(
            "/api/approvals/requests",
            params={"compliance_review_id": review["id"]},
            headers=headers,
        )
    ).json()[0]["id"]

    async with db_session_factory() as session:
        expired_count = await expire_stale_approval_requests(session)
    assert expired_count == 0

    detail = await client.get(f"/api/approvals/requests/{request_id}", headers=headers)
    assert detail.json()["status"] == "pending"
