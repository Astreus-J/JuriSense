"""FEATURE-7.3 / STORY-7.3.1: the Decision Passport read-model API
(`GET /api/decisions/{decision_id}/passport`) renders the full "why was this approved?"
narrative -- decision id, supplier, contract, document hashes, policies evaluated (with
version), rules triggered, external sources consulted, AI executions, reviewers, final
decision, and timestamp -- all sourced from the immutable records built in EPIC-2 through
EPIC-7.

Driven through the real endpoints, so each Decision path is exercised exactly as production
creates it, the same discipline `test_evidence_package.py` follows for the raw package.
"""

import uuid

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.approvals.infrastructure.models import Decision
from app.evidence.application import decision_passport_service
from tests.approvals.conftest import create_supplier, register_org_and_login
from tests.approvals.lifecycle_helpers import finance_review_chain
from tests.evidence.test_evidence_package import _block_review, _decision_for_review
from tests.policies.test_compliance_review import (
    EVIDENCE_ENVELOPE,
    SANC_001_YAML,
    TAX_ID,
    _upload_contract,
)


async def test_block_decision_passport_renders_the_full_narrative(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
) -> None:
    headers, contract_version_id, review_id = await _block_review(
        client,
        db_session_factory,
        email="passport-block@example.com",
        mock_openrouter=mock_openrouter,
        mock_cnpj_registry=mock_cnpj_registry,
        seed_sanctions_index=seed_sanctions_index,
        rule_yamls=[SANC_001_YAML],
    )
    decision = await _decision_for_review(db_session_factory, review_id)

    response = await client.get(f"/api/decisions/{decision.id}/passport", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["decision_id"] == str(decision.id)
    assert body["status"] == "BLOCK"
    assert body["lifecycle"] == "ACTIVE"
    assert body["overridden"] is False
    assert body["override_justification"] is None
    assert body["supersedes_decision_id"] is None
    # QA review (2026-10-06): "timestamp" is a named acceptance-criteria field; check it
    # actually round-trips the real Decision row's own values, not just that it's present.
    assert body["created_at"][:19] == decision.created_at.isoformat()[:19]
    assert body["valid_until"][:19] == decision.valid_until.isoformat()[:19]

    assert body["supplier_legal_name"] == "Test Supplier Ltda."
    assert body["supplier_tax_id"] == TAX_ID

    assert body["contract_title"] == "High-Value MSA"
    assert body["contract_version_id"] == contract_version_id
    assert body["contract_version_number"] == 1

    [document] = body["documents"]
    assert document["content_hash"]
    assert document["mime_type"] == "application/pdf"

    assert body["ai_execution"]["model_name"]
    assert body["ai_execution"]["prompt_version"]

    assert len(body["policy_versions"]) == 1
    assert body["policy_versions"][0]["version_number"] == 1

    rule_keys = {rule["rule_key"] for rule in body["rule_evaluations"]}
    assert "SANC-001" in rule_keys
    [sanc_rule] = [r for r in body["rule_evaluations"] if r["rule_key"] == "SANC-001"]
    assert sanc_rule["rule_name"]
    assert sanc_rule["outcome"] == "BLOCK"
    assert sanc_rule["rationale"]

    assert body["external_sources_consulted"], "a sanctions-hit BLOCK must cite its source"
    assert body["reviewers"] == []  # BLOCK has no approval chain

    assert body["evidence_package_id"]
    assert body["merkle_root"]
    assert body["evidence_count"] > 0


async def test_approve_chain_passport_includes_the_resolved_reviewer(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
) -> None:
    chain = await finance_review_chain(
        client,
        db_session_factory,
        email="passport-chain@example.com",
        mock_openrouter=mock_openrouter,
        mock_cnpj_registry=mock_cnpj_registry,
        seed_sanctions_index=seed_sanctions_index,
    )

    response = await client.get(
        f"/api/decisions/{chain['decision_id']}/passport", headers=chain["admin_headers"]
    )
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["status"] == "APPROVE"
    [reviewer] = body["reviewers"]
    assert reviewer["approver_role"] == "legal"
    assert reviewer["status"] == "approved"
    assert reviewer["resolved_by"] is not None
    assert reviewer["step_number"] == 1


async def test_overridden_decision_passport_reflects_the_override(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
) -> None:
    chain = await finance_review_chain(
        client,
        db_session_factory,
        email="passport-override@example.com",
        mock_openrouter=mock_openrouter,
        mock_cnpj_registry=mock_cnpj_registry,
        seed_sanctions_index=seed_sanctions_index,
    )

    override = await client.post(
        f"/api/decisions/{chain['decision_id']}/override",
        json={"new_status": "BLOCK", "justification": "Counterparty flagged after the fact"},
        headers=chain["admin_headers"],
    )
    assert override.status_code == 200, override.text

    response = await client.get(
        f"/api/decisions/{chain['decision_id']}/passport", headers=chain["admin_headers"]
    )
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["status"] == "BLOCK"
    assert body["overridden"] is True
    assert body["override_justification"] == "Counterparty flagged after the fact"


async def test_approve_only_decision_passport_has_no_policies_or_reviewers(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    run_contract_extraction_inline,
) -> None:
    """Mirrors `test_evidence_package.test_approve_decision_gets_exactly_one_package`: no
    published policy means nothing was pooled, and APPROVE has no approval chain -- the
    passport must render that as empty lists, not omit the fields or error."""
    mock_openrouter(payload=EVIDENCE_ENVELOPE)
    headers = await register_org_and_login(client, "passport-approve-only@example.com")
    supplier = await create_supplier(client, headers, tax_id=TAX_ID)
    contract_version_id = await _upload_contract(client, headers, supplier["id"])
    review = (
        await client.post(
            "/api/compliance/reviews",
            json={"contract_version_id": contract_version_id},
            headers=headers,
        )
    ).json()
    assert review["status"] == "APPROVE"

    async with db_session_factory() as session:
        decision = (
            await session.execute(
                select(Decision).where(Decision.compliance_review_id == uuid.UUID(review["id"]))
            )
        ).scalar_one()

    response = await client.get(f"/api/decisions/{decision.id}/passport", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["policy_versions"] == []
    assert body["rule_evaluations"] == []
    assert body["reviewers"] == []
    assert body["external_sources_consulted"] == []
    assert body["supplier_legal_name"] == "Test Supplier Ltda."


async def test_a_broken_internal_reference_is_404_not_an_unhandled_500(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    run_contract_extraction_inline,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Security review (2026-10-06): `get_decision_passport` raises the base `EvidenceError`
    (not just `EvidencePackageNotFoundError`) when one of its own evidence-port calls can't
    resolve a reference the Decision's package assembly already proved existed. Forces that
    branch directly -- genuinely unreachable in production today, since nothing deletes a
    ComplianceReview/ContractVersion/Supplier -- to prove the route's 404 contract holds even
    there, rather than leaking an unhandled 500."""
    mock_openrouter(payload=EVIDENCE_ENVELOPE)
    headers = await register_org_and_login(client, "passport-broken-ref@example.com")
    supplier = await create_supplier(client, headers, tax_id=TAX_ID)
    contract_version_id = await _upload_contract(client, headers, supplier["id"])
    review = (
        await client.post(
            "/api/compliance/reviews",
            json={"contract_version_id": contract_version_id},
            headers=headers,
        )
    ).json()
    assert review["status"] == "APPROVE"

    async with db_session_factory() as session:
        decision = (
            await session.execute(
                select(Decision).where(Decision.compliance_review_id == uuid.UUID(review["id"]))
            )
        ).scalar_one()

    async def _missing_review(*args: object, **kwargs: object) -> None:
        return None

    monkeypatch.setattr(decision_passport_service, "get_review_evidence", _missing_review)

    response = await client.get(f"/api/decisions/{decision.id}/passport", headers=headers)
    assert response.status_code == 404, response.text
