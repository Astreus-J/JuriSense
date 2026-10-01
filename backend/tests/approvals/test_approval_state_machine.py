"""FEATURE-6.1 routing (APR-001/APR-003) + FEATURE-6.2 state machine (APR-002,
BR-APR-001/BR-APR-002): role-matched resolution, multi-step chain instantiation,
rejection halting the chain, and `ApprovalRequest` immutability once resolved.
"""

import uuid

import httpx
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.approvals.infrastructure.models import ApprovalRequest
from app.approvals.infrastructure.repositories import DecisionRepository
from app.identity.infrastructure.repositories import UserRepository
from tests.approvals.conftest import (
    ACTIVE_CNPJ_RESPONSE,
    create_supplier,
    create_user_and_login,
    register_org_and_login,
)
from tests.policies.test_compliance_review import (
    EVIDENCE_ENVELOPE,
    FIN_003_YAML,
    LEGAL_008_YAML,
    TAX_ID,
    _create_policy_with_rules,
    _upload_contract,
)


async def _trigger_review(
    client: httpx.AsyncClient, headers: dict, *, rule_yamls: list[str]
) -> dict:
    supplier = await create_supplier(client, headers, tax_id=TAX_ID)
    contract_version_id = await _upload_contract(client, headers, supplier["id"])
    await _create_policy_with_rules(client, headers, name="Vendor Policy", rule_yamls=rule_yamls)
    response = await client.post(
        "/api/compliance/reviews",
        json={"contract_version_id": contract_version_id},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _organization_id_for(db_session_factory: async_sessionmaker, email: str):
    async with db_session_factory() as session:
        user = await UserRepository(session).get_by_email(email)
        return user.organization_id


async def test_medium_severity_review_routes_to_single_legal_step(
    client: httpx.AsyncClient,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
) -> None:
    """STORY-6.1.1 (APR-001): a MEDIUM-severity REVIEW (FIN-003, medium/legal) routes to
    the organization's MEDIUM-tier workflow -- a single Legal step -- regardless that
    FIN-003's own `approver_role` happens to also be "legal" (the workflow is keyed by
    severity tier, not by the triggering rule)."""
    mock_cnpj_registry(data=ACTIVE_CNPJ_RESPONSE)
    await seed_sanctions_index(hit_document=TAX_ID)
    mock_openrouter(payload=EVIDENCE_ENVELOPE)

    admin_headers = await register_org_and_login(client, "medium-route@example.com")
    review = await _trigger_review(client, admin_headers, rule_yamls=[FIN_003_YAML])
    assert review["status"] == "REVIEW"

    response = await client.get(
        "/api/approvals/requests",
        params={"compliance_review_id": review["id"]},
        headers=admin_headers,
    )
    assert response.status_code == 200, response.text
    requests = response.json()
    assert len(requests) == 1
    assert requests[0]["approver_role"] == "legal"
    assert requests[0]["step_number"] == 1
    assert requests[0]["status"] == "pending"


async def test_wrong_role_cannot_resolve_and_request_stays_pending(
    client: httpx.AsyncClient,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
) -> None:
    """BR-APR-001/APR-002: the admin has `update` RBAC permission on the `approvals`
    module (the grid's CRUD-everywhere role) but is NOT the matching `approver_role`
    ("legal") -- the role-match guard is a *separate* check from the RBAC permission
    grid, and must still refuse."""
    mock_cnpj_registry(data=ACTIVE_CNPJ_RESPONSE)
    await seed_sanctions_index(hit_document=TAX_ID)
    mock_openrouter(payload=EVIDENCE_ENVELOPE)

    admin_headers = await register_org_and_login(client, "wrong-role@example.com")
    review = await _trigger_review(client, admin_headers, rule_yamls=[FIN_003_YAML])
    requests = (
        await client.get(
            "/api/approvals/requests",
            params={"compliance_review_id": review["id"]},
            headers=admin_headers,
        )
    ).json()
    request_id = requests[0]["id"]

    response = await client.post(
        f"/api/approvals/requests/{request_id}/approve", json={}, headers=admin_headers
    )
    assert response.status_code == 403, response.text

    detail = await client.get(f"/api/approvals/requests/{request_id}", headers=admin_headers)
    assert detail.json()["status"] == "pending"


async def test_matching_role_approves_single_step_review_and_creates_approve_decision(
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

    admin_headers = await register_org_and_login(client, "approve-final@example.com")
    legal_headers = await create_user_and_login(
        client, admin_headers, email="legal-approve-final@example.com", role="legal"
    )
    review = await _trigger_review(client, admin_headers, rule_yamls=[FIN_003_YAML])
    requests = (
        await client.get(
            "/api/approvals/requests",
            params={"compliance_review_id": review["id"]},
            headers=admin_headers,
        )
    ).json()
    request_id = requests[0]["id"]

    response = await client.post(
        f"/api/approvals/requests/{request_id}/approve",
        json={"justification": "Looks fine"},
        headers=legal_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "approved"
    assert body["resolved_by"] is not None
    assert body["resolved_at"] is not None

    organization_id = await _organization_id_for(db_session_factory, "approve-final@example.com")
    async with db_session_factory() as session:
        decision = await DecisionRepository(session).get_by_review(
            uuid.UUID(review["id"]), organization_id
        )
    assert decision is not None
    assert decision.status == "APPROVE"


async def test_high_severity_review_multistep_chain_in_order(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
) -> None:
    """STORY-6.1.2/APR-003: a HIGH-severity review (LEGAL-008, high/legal) routes through
    the FULL HIGH-tier chain (Compliance -> Legal -> Director) regardless that
    LEGAL-008's own `approver_role` is just "legal" -- only step 1 is instantiated
    initially; approving step 1 instantiates step 2; approving the final step creates the
    Decision.

    Steps 1/2 ("compliance"/"legal") are exercised through the real HTTP API with real
    users. Step 3 ("director") cannot be: `app.identity.domain.constants.Role` has no
    "director" value at all -- the closest real role is the generic "approver" persona
    (see `app.identity.domain.rbac`'s own module docstring: "the generic Director/
    Approver persona") -- so there is no way to provision a "director"-role user through
    the public `POST /api/users` API. This is a real, pre-existing gap between
    `docs/03-domain/approvals.md`'s routing-table vocabulary and Identity's actual `Role`
    enum, not something this epic's scope includes fixing (see this suite's final report
    for the write-up). Step 3 is instead exercised directly at the application layer,
    with a hand-crafted `User`/`Membership(role="director")` inserted straight into the
    test database -- `approval_service.approve_request` only ever checks
    `Membership.role` (BR-APR-001), never the RBAC permission grid (that is the FastAPI
    route dependency's separate concern), so this still faithfully exercises the same
    state-machine code a real HTTP call would run.
    """
    mock_cnpj_registry(data=ACTIVE_CNPJ_RESPONSE)
    await seed_sanctions_index(hit_document=TAX_ID)
    mock_openrouter(payload=EVIDENCE_ENVELOPE)

    admin_headers = await register_org_and_login(client, "high-chain@example.com")
    compliance_headers = await create_user_and_login(
        client, admin_headers, email="compliance-high-chain@example.com", role="compliance"
    )
    legal_headers = await create_user_and_login(
        client, admin_headers, email="legal-high-chain@example.com", role="legal"
    )

    review = await _trigger_review(client, admin_headers, rule_yamls=[LEGAL_008_YAML])
    assert review["status"] == "REVIEW"

    async def _list_requests() -> list[dict]:
        resp = await client.get(
            "/api/approvals/requests",
            params={"compliance_review_id": review["id"]},
            headers=admin_headers,
        )
        assert resp.status_code == 200, resp.text
        return resp.json()

    # Only step 1 (compliance) exists initially -- steps 2/3 are NOT pre-instantiated.
    requests = await _list_requests()
    assert len(requests) == 1
    assert requests[0]["approver_role"] == "compliance"
    assert requests[0]["step_number"] == 1

    step1_response = await client.post(
        f"/api/approvals/requests/{requests[0]['id']}/approve", json={}, headers=compliance_headers
    )
    assert step1_response.status_code == 200, step1_response.text

    requests = await _list_requests()
    assert len(requests) == 2
    assert requests[1]["approver_role"] == "legal"
    assert requests[1]["step_number"] == 2
    assert requests[1]["status"] == "pending"

    step2_response = await client.post(
        f"/api/approvals/requests/{requests[1]['id']}/approve", json={}, headers=legal_headers
    )
    assert step2_response.status_code == 200, step2_response.text

    requests = await _list_requests()
    assert len(requests) == 3
    assert requests[2]["approver_role"] == "director"
    assert requests[2]["step_number"] == 3
    assert requests[2]["status"] == "pending"

    organization_id = await _organization_id_for(db_session_factory, "high-chain@example.com")

    # No Decision exists yet -- the chain hasn't resolved.
    async with db_session_factory() as session:
        decision = await DecisionRepository(session).get_by_review(
            uuid.UUID(review["id"]), organization_id
        )
    assert decision is None

    from app.approvals.application.approval_service import approve_request as _approve_request
    from app.core import security
    from app.identity.domain.constants import MembershipStatus
    from app.identity.infrastructure.models import Membership, User

    async with db_session_factory() as session:
        director = User(
            organization_id=organization_id,
            full_name="Director",
            email="director-high-chain@example.com",
            password_hash=security.hash_password("StrongPass1"),
            role="director",
        )
        session.add(director)
        await session.flush()
        session.add(
            Membership(
                user_id=director.id,
                organization_id=organization_id,
                role="director",
                status=MembershipStatus.ACTIVE.value,
            )
        )
        await session.commit()
        director_id = director.id

    async with db_session_factory() as session:
        resolved = await _approve_request(
            session,
            organization_id=organization_id,
            actor_id=director_id,
            request_id=uuid.UUID(requests[2]["id"]),
            justification=None,
        )
    assert resolved.status == "approved"

    async with db_session_factory() as session:
        decision = await DecisionRepository(session).get_by_review(
            uuid.UUID(review["id"]), organization_id
        )
    assert decision is not None
    assert decision.status == "APPROVE"


async def test_rejection_halts_the_chain_and_produces_a_block_decision(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
) -> None:
    """BR-APR-002: a rejection at step 1 of a 3-step HIGH chain halts it immediately --
    steps 2/3 are NEVER instantiated -- and produces a `Decision` with `status="BLOCK"`
    (docs/03-domain/approvals.md: "treated as equivalent in severity to a BLOCK-class
    outcome")."""
    mock_cnpj_registry(data=ACTIVE_CNPJ_RESPONSE)
    await seed_sanctions_index(hit_document=TAX_ID)
    mock_openrouter(payload=EVIDENCE_ENVELOPE)

    admin_headers = await register_org_and_login(client, "reject-chain@example.com")
    compliance_headers = await create_user_and_login(
        client, admin_headers, email="compliance-reject-chain@example.com", role="compliance"
    )
    review = await _trigger_review(client, admin_headers, rule_yamls=[LEGAL_008_YAML])

    requests = (
        await client.get(
            "/api/approvals/requests",
            params={"compliance_review_id": review["id"]},
            headers=admin_headers,
        )
    ).json()
    assert len(requests) == 1
    request_id = requests[0]["id"]

    # Rejection requires a non-empty justification.
    empty_justification = await client.post(
        f"/api/approvals/requests/{request_id}/reject",
        json={"justification": ""},
        headers=compliance_headers,
    )
    assert empty_justification.status_code == 422, empty_justification.text

    response = await client.post(
        f"/api/approvals/requests/{request_id}/reject",
        json={"justification": "Sanctions concern not fully resolved"},
        headers=compliance_headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "rejected"

    # No step 2 was ever instantiated.
    requests_after = (
        await client.get(
            "/api/approvals/requests",
            params={"compliance_review_id": review["id"]},
            headers=admin_headers,
        )
    ).json()
    assert len(requests_after) == 1

    organization_id = await _organization_id_for(db_session_factory, "reject-chain@example.com")
    async with db_session_factory() as session:
        decision = await DecisionRepository(session).get_by_review(
            uuid.UUID(review["id"]), organization_id
        )
    assert decision is not None
    assert decision.status == "BLOCK"


async def test_resolving_an_already_resolved_request_raises(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
) -> None:
    """domain-model.md: an `ApprovalRequest` is immutable once resolved. Checked both at
    the API/application layer (a second resolution attempt 409s) and, mirroring
    `Rule._guard_frozen`'s own test, at the ORM layer directly."""
    mock_cnpj_registry(data=ACTIVE_CNPJ_RESPONSE)
    await seed_sanctions_index(hit_document=TAX_ID)
    mock_openrouter(payload=EVIDENCE_ENVELOPE)

    admin_headers = await register_org_and_login(client, "immutable@example.com")
    legal_headers = await create_user_and_login(
        client, admin_headers, email="legal-immutable@example.com", role="legal"
    )
    review = await _trigger_review(client, admin_headers, rule_yamls=[FIN_003_YAML])
    request_id = (
        await client.get(
            "/api/approvals/requests",
            params={"compliance_review_id": review["id"]},
            headers=admin_headers,
        )
    ).json()[0]["id"]

    first = await client.post(
        f"/api/approvals/requests/{request_id}/approve", json={}, headers=legal_headers
    )
    assert first.status_code == 200, first.text

    second = await client.post(
        f"/api/approvals/requests/{request_id}/approve", json={}, headers=legal_headers
    )
    assert second.status_code == 409, second.text

    third = await client.post(
        f"/api/approvals/requests/{request_id}/reject",
        json={"justification": "too late"},
        headers=legal_headers,
    )
    assert third.status_code == 409, third.text

    # ORM-level guard, direct mutation attempt (mirrors Rule._guard_frozen's own test).
    import pytest

    from app.approvals.domain.errors import ApprovalRequestAlreadyResolvedError

    async with db_session_factory() as session:
        loaded = await session.get(ApprovalRequest, uuid.UUID(request_id))
        assert loaded is not None
        assert loaded.status == "approved"
        with pytest.raises(ApprovalRequestAlreadyResolvedError):
            loaded.justification = "tampered"


async def test_approval_requests_are_scoped_to_the_caller_organization(
    client: httpx.AsyncClient,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
) -> None:
    """Multi-tenancy (ADR-003/CLAUDE.md): another organization's ApprovalRequest, and
    another organization's ComplianceReview used as a list filter, are both 404s, never
    a cross-tenant leak."""
    mock_cnpj_registry(data=ACTIVE_CNPJ_RESPONSE)
    await seed_sanctions_index(hit_document=TAX_ID)
    mock_openrouter(payload=EVIDENCE_ENVELOPE)

    owner_headers = await register_org_and_login(client, "tenant-owner-apr@example.com")
    review = await _trigger_review(client, owner_headers, rule_yamls=[FIN_003_YAML])
    request_id = (
        await client.get(
            "/api/approvals/requests",
            params={"compliance_review_id": review["id"]},
            headers=owner_headers,
        )
    ).json()[0]["id"]

    outsider_headers = await register_org_and_login(client, "tenant-outsider-apr@example.com")

    get_request = await client.get(
        f"/api/approvals/requests/{request_id}", headers=outsider_headers
    )
    assert get_request.status_code == 404

    list_requests = await client.get(
        "/api/approvals/requests",
        params={"compliance_review_id": review["id"]},
        headers=outsider_headers,
    )
    assert list_requests.status_code == 404

    approve_attempt = await client.post(
        f"/api/approvals/requests/{request_id}/approve", json={}, headers=outsider_headers
    )
    assert approve_attempt.status_code == 404
