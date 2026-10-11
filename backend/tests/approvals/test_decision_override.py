"""FEATURE-6.3/STORY-6.3.2 (DEC-002, BR-DEC-003): authorized manual override of a
`Decision`, with mandatory non-empty justification, that never touches the underlying
`RuleEvaluation`/`ApprovalRequest` records.
"""

import uuid

import httpx
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.approvals.infrastructure.repositories import DecisionRepository
from app.evidence.infrastructure.repositories import AuditEventRepository
from app.identity.infrastructure.repositories import UserRepository
from app.policies.infrastructure.repositories import RuleEvaluationRepository
from tests.approvals.conftest import (
    ACTIVE_CNPJ_RESPONSE,
    create_supplier,
    register_org_and_login,
)
from tests.policies.test_compliance_review import (
    EVIDENCE_ENVELOPE,
    SANC_001_YAML,
    TAX_ID,
    _create_policy_with_rules,
    _upload_contract,
)


async def _block_decision(client: httpx.AsyncClient, headers: dict) -> dict:
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
    return response.json()


async def test_override_requires_non_empty_justification(
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

    headers = await register_org_and_login(client, "override-empty@example.com")
    review = await _block_decision(client, headers)

    async with db_session_factory() as session:
        admin = await UserRepository(session).get_by_email("override-empty@example.com")
        decision = await DecisionRepository(session).get_by_review(
            uuid.UUID(review["id"]), admin.organization_id
        )
    decision_id = decision.id

    response = await client.post(
        f"/api/decisions/{decision_id}/override",
        json={"new_status": "APPROVE", "justification": ""},
        headers=headers,
    )
    assert response.status_code == 422, response.text

    unchanged = await client.get(f"/api/decisions/{decision_id}", headers=headers)
    assert unchanged.json()["status"] == "BLOCK"
    assert unchanged.json()["overridden"] is False


async def test_override_changes_status_without_touching_original_evaluation_records(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
) -> None:
    """BR-DEC-003: override sets `overridden=True`/`override_justification`/`status` in
    place, but the original `RuleEvaluation` rows for the review (and the `ApprovalRequest`
    set, empty here since BLOCK has none) remain provably untouched afterward."""
    mock_cnpj_registry(data=ACTIVE_CNPJ_RESPONSE)
    await seed_sanctions_index(hit_document=TAX_ID)
    mock_openrouter(payload=EVIDENCE_ENVELOPE)

    headers = await register_org_and_login(client, "override-ok@example.com")
    review = await _block_decision(client, headers)

    async with db_session_factory() as session:
        admin = await UserRepository(session).get_by_email("override-ok@example.com")
        organization_id = admin.organization_id
        review_id = uuid.UUID(review["id"])
        decision = await DecisionRepository(session).get_by_review(review_id, organization_id)
        evaluations_before = await RuleEvaluationRepository(session).list_by_review(review_id)
    decision_id = decision.id
    evaluations_snapshot = [
        (e.id, e.outcome, e.rationale, e.created_at) for e in evaluations_before
    ]
    assert len(evaluations_snapshot) == 1  # SANC-001's own RuleEvaluation

    response = await client.post(
        f"/api/decisions/{decision_id}/override",
        json={
            "new_status": "APPROVE",
            "justification": "Sanctions hit confirmed as a false-positive name clash",
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "APPROVE"
    assert body["overridden"] is True
    assert body["override_justification"] == (
        "Sanctions hit confirmed as a false-positive name clash"
    )

    async with db_session_factory() as session:
        evaluations_after = await RuleEvaluationRepository(session).list_by_review(review_id)
    evaluations_after_snapshot = [
        (e.id, e.outcome, e.rationale, e.created_at) for e in evaluations_after
    ]
    assert evaluations_after_snapshot == evaluations_snapshot
    # Still exactly one RuleEvaluation row -- override never deletes or adds to it.
    assert evaluations_after_snapshot[0][1] == "BLOCK"  # original outcome, unedited


async def test_decisions_are_scoped_to_the_caller_organization(
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

    owner_headers = await register_org_and_login(client, "tenant-owner-dec@example.com")
    review = await _block_decision(client, owner_headers)

    async with db_session_factory() as session:
        admin = await UserRepository(session).get_by_email("tenant-owner-dec@example.com")
        decision = await DecisionRepository(session).get_by_review(
            uuid.UUID(review["id"]), admin.organization_id
        )
    decision_id = decision.id

    outsider_headers = await register_org_and_login(client, "tenant-outsider-dec@example.com")

    get_response = await client.get(f"/api/decisions/{decision_id}", headers=outsider_headers)
    assert get_response.status_code == 404

    override_response = await client.post(
        f"/api/decisions/{decision_id}/override",
        json={"new_status": "APPROVE", "justification": "not mine to override"},
        headers=outsider_headers,
    )
    assert override_response.status_code == 404


async def test_override_appends_a_chained_addendum_to_the_evidence_package(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
) -> None:
    """#187: override_decision used to change `Decision.status` in place without ever
    touching the EvidencePackage already assembled for it, leaving anchored evidence stale.
    Every override now appends a chained, anchorable `EvidenceOverrideAddendum`."""
    mock_cnpj_registry(data=ACTIVE_CNPJ_RESPONSE)
    await seed_sanctions_index(hit_document=TAX_ID)
    mock_openrouter(payload=EVIDENCE_ENVELOPE)

    headers = await register_org_and_login(client, "override-addendum@example.com")
    review = await _block_decision(client, headers)

    async with db_session_factory() as session:
        admin = await UserRepository(session).get_by_email("override-addendum@example.com")
        organization_id = admin.organization_id
        decision = await DecisionRepository(session).get_by_review(
            uuid.UUID(review["id"]), organization_id
        )
    decision_id = decision.id

    first = await client.post(
        f"/api/decisions/{decision_id}/override",
        json={"new_status": "APPROVE", "justification": "Sanctions hit was a false positive"},
        headers=headers,
    )
    assert first.status_code == 200, first.text

    package_response = await client.get(
        f"/api/decisions/{decision_id}/evidence-package", headers=headers
    )
    assert package_response.status_code == 200, package_response.text
    package_id = package_response.json()["id"]
    addenda = package_response.json()["override_addenda"]
    assert len(addenda) == 1
    [first_addendum] = addenda
    assert first_addendum["sequence_number"] == 1
    assert first_addendum["previous_hash"] is None
    assert first_addendum["original_status"] == "BLOCK"
    assert first_addendum["new_status"] == "APPROVE"
    assert first_addendum["decision_id"] == str(decision_id)
    assert first_addendum["evidence_package_id"] == package_id
    assert first_addendum["content_hash"]

    async with db_session_factory() as session:
        events = await AuditEventRepository(session).list(
            organization_id=organization_id, event_type="evidence.override_addendum_recorded"
        )
    assert len(events) == 1
    assert events[0].payload["sequence_number"] == 1
    assert events[0].payload["content_hash"] == first_addendum["content_hash"]

    # A second override on the same (still-ACTIVE) Decision extends the chain.
    second = await client.post(
        f"/api/decisions/{decision_id}/override",
        json={"new_status": "BLOCK", "justification": "Reassessed: the hit was genuine"},
        headers=headers,
    )
    assert second.status_code == 200, second.text

    package_response_2 = await client.get(
        f"/api/decisions/{decision_id}/evidence-package", headers=headers
    )
    addenda_2 = package_response_2.json()["override_addenda"]
    assert len(addenda_2) == 2
    second_addendum = next(a for a in addenda_2 if a["sequence_number"] == 2)
    assert second_addendum["previous_hash"] == first_addendum["content_hash"]
    assert second_addendum["original_status"] == "APPROVE"
    assert second_addendum["new_status"] == "BLOCK"
    assert second_addendum["content_hash"] != first_addendum["content_hash"]
