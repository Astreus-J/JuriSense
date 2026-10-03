"""EVD-001 (STORY-7.1.1): every Decision gets exactly one EvidencePackage, assembled in the same
unit as the Decision; EVD-002 / BR-EVD-001 (STORY-7.1.2): the stored merkle_root is recomputable
from the persisted Evidence rows, and recomputation matches it.

Driven through the real endpoints (`/api/compliance/reviews`, `/api/decisions/...`), so each
Decision path is exercised exactly as production creates it.
"""

import json
import uuid

import httpx
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.approvals.domain.evidence import DecisionFacts
from app.approvals.infrastructure.models import Decision
from app.evidence.application import evidence_package_service
from app.evidence.infrastructure.models import Evidence, EvidencePackage
from app.evidence.infrastructure.repositories import AuditEventRepository
from app.identity.infrastructure.repositories import UserRepository
from app.policies.infrastructure.models import RuleEvaluation
from tests.approvals.conftest import ACTIVE_CNPJ_RESPONSE, create_supplier, register_org_and_login
from tests.approvals.lifecycle_helpers import finance_review_chain
from tests.policies.test_compliance_review import (
    EVIDENCE_ENVELOPE,
    SANC_001_YAML,
    TAX_ID,
    _create_policy_with_rules,
    _upload_contract,
)


async def _organization_id(db_session_factory: async_sessionmaker, email: str) -> uuid.UUID:
    async with db_session_factory() as session:
        return (await UserRepository(session).get_by_email(email)).organization_id


async def _decision_for_review(db_session_factory: async_sessionmaker, review_id: str) -> Decision:
    async with db_session_factory() as session:
        result = await session.execute(
            select(Decision).where(Decision.compliance_review_id == uuid.UUID(review_id))
        )
        return result.scalar_one()


async def _package_rows(db_session_factory: async_sessionmaker, decision_id: uuid.UUID):
    async with db_session_factory() as session:
        packages = (
            (
                await session.execute(
                    select(EvidencePackage).where(EvidencePackage.decision_id == decision_id)
                )
            )
            .scalars()
            .all()
        )
        evidence = (
            (
                await session.execute(
                    select(Evidence).where(
                        Evidence.evidence_package_id.in_([p.id for p in packages])
                    )
                )
            )
            .scalars()
            .all()
        )
        return packages, evidence


async def _recompute(db_session_factory: async_sessionmaker, package_id: uuid.UUID):
    """A fresh session, so nothing comes from an identity map: this is the 'process restart'
    recomputation of BR-EVD-001."""
    async with db_session_factory() as session:
        return await evidence_package_service.recompute(
            session,
            organization_id=(await session.get(EvidencePackage, package_id)).organization_id,
            package_id=package_id,
        )


async def _block_review(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    *,
    email: str,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    rule_yamls: list[str],
) -> tuple[dict, str, str]:
    """Creates the org, supplier, contract version and policy, then triggers one review.
    Returns (headers, contract_version_id, review_id)."""
    mock_cnpj_registry(data=ACTIVE_CNPJ_RESPONSE)
    await seed_sanctions_index(hit_document=TAX_ID)
    mock_openrouter(payload=EVIDENCE_ENVELOPE)
    headers = await register_org_and_login(client, email)
    supplier = await create_supplier(client, headers, tax_id=TAX_ID)
    contract_version_id = await _upload_contract(client, headers, supplier["id"])
    await _create_policy_with_rules(client, headers, name="Vendor Policy", rule_yamls=rule_yamls)
    response = await client.post(
        "/api/compliance/reviews",
        json={"contract_version_id": contract_version_id},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return headers, contract_version_id, response.json()["id"]


async def test_block_decision_gets_exactly_one_package_with_the_full_leaf_catalog(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
) -> None:
    headers, _, review_id = await _block_review(
        client,
        db_session_factory,
        email="pkg-block@example.com",
        mock_openrouter=mock_openrouter,
        mock_cnpj_registry=mock_cnpj_registry,
        seed_sanctions_index=seed_sanctions_index,
        rule_yamls=[SANC_001_YAML],
    )
    decision = await _decision_for_review(db_session_factory, review_id)
    assert decision.status == "BLOCK"

    packages, evidence = await _package_rows(db_session_factory, decision.id)
    assert len(packages) == 1
    assert packages[0].evidence_count == len(evidence)

    types = {row.type for row in evidence}
    assert {
        "decision",
        "contract_version",
        "document",
        "ai_execution",
        "policy_version",
        "rule_evaluation",
        "contract_field",
        "supplier_check",
    } <= types
    assert "reviewer" not in types  # BLOCK has no approval chain

    response = await client.get(f"/api/decisions/{decision.id}/evidence-package", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == str(packages[0].id)
    assert body["merkle_root"] == packages[0].merkle_root

    by_type = {row["type"]: row for row in body["evidence"]}
    assert by_type["decision"]["payload"]["status"] == "BLOCK"
    assert by_type["document"]["payload"]["content_hash"]
    assert by_type["ai_execution"]["payload"]["model_name"]
    assert by_type["ai_execution"]["payload"]["prompt_version"]


async def test_block_package_holds_commitments_not_raw_contract_or_personal_data(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
) -> None:
    """BR-EVD-002 spirit: payloads commit to content, they never carry it. The supplier's tax id
    and the rule rationale text (which quotes contract terms) must not appear in any payload."""
    _, _, review_id = await _block_review(
        client,
        db_session_factory,
        email="pkg-privacy@example.com",
        mock_openrouter=mock_openrouter,
        mock_cnpj_registry=mock_cnpj_registry,
        seed_sanctions_index=seed_sanctions_index,
        rule_yamls=[SANC_001_YAML],
    )
    decision = await _decision_for_review(db_session_factory, review_id)
    _, evidence = await _package_rows(db_session_factory, decision.id)
    serialized = json.dumps([row.payload for row in evidence])

    assert TAX_ID not in serialized
    async with db_session_factory() as session:
        rationales = [
            row.rationale for row in (await session.execute(select(RuleEvaluation))).scalars()
        ]
    assert rationales, "the BLOCK review should have produced at least one rule evaluation"
    for rationale in rationales:
        assert rationale not in serialized


async def test_approve_decision_gets_exactly_one_package(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    run_contract_extraction_inline,
) -> None:
    mock_openrouter(payload=EVIDENCE_ENVELOPE)
    headers = await register_org_and_login(client, "pkg-approve@example.com")
    supplier = await create_supplier(client, headers, tax_id=TAX_ID)
    contract_version_id = await _upload_contract(client, headers, supplier["id"])
    response = await client.post(
        "/api/compliance/reviews",
        json={"contract_version_id": contract_version_id},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    review = response.json()
    assert review["status"] == "APPROVE"

    decision = await _decision_for_review(db_session_factory, review["id"])
    packages, evidence = await _package_rows(db_session_factory, decision.id)
    assert len(packages) == 1
    types = {row.type for row in evidence}
    assert {"decision", "contract_version", "document", "ai_execution"} <= types
    assert "reviewer" not in types
    assert "policy_version" not in types  # no published policy, nothing pooled

    response = await client.get(f"/api/decisions/{decision.id}/evidence-package", headers=headers)
    assert response.status_code == 200, response.text


async def test_review_chain_resolved_to_approve_records_the_human_reviewers(
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
        email="pkg-chain@example.com",
        mock_openrouter=mock_openrouter,
        mock_cnpj_registry=mock_cnpj_registry,
        seed_sanctions_index=seed_sanctions_index,
    )
    decision_id = chain["decision_id"]
    packages, evidence = await _package_rows(db_session_factory, decision_id)
    assert len(packages) == 1

    reviewers = [row for row in evidence if row.type == "reviewer"]
    assert len(reviewers) == 1
    [reviewer] = reviewers
    assert reviewer.payload["approver_role"] == "legal"
    assert reviewer.payload["status"] == "approved"
    assert reviewer.payload["resolved_by"] is not None
    assert reviewer.payload["step_number"] == 1

    recomputed = await _recompute(db_session_factory, packages[0].id)
    assert recomputed.matches is True


async def test_rerunning_assembly_for_the_same_decision_is_a_no_op(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    run_contract_extraction_inline,
) -> None:
    mock_openrouter(payload=EVIDENCE_ENVELOPE)
    headers = await register_org_and_login(client, "pkg-idempotent@example.com")
    supplier = await create_supplier(client, headers, tax_id=TAX_ID)
    contract_version_id = await _upload_contract(client, headers, supplier["id"])
    review = (
        await client.post(
            "/api/compliance/reviews",
            json={"contract_version_id": contract_version_id},
            headers=headers,
        )
    ).json()
    decision = await _decision_for_review(db_session_factory, review["id"])
    organization_id = await _organization_id(db_session_factory, "pkg-idempotent@example.com")
    packages_before, evidence_before = await _package_rows(db_session_factory, decision.id)

    async with db_session_factory() as session:
        audit_before = len(
            await AuditEventRepository(session).list(
                organization_id=organization_id, event_type="evidence.package_created"
            )
        )
    async with db_session_factory() as session:
        again = await evidence_package_service.assemble_evidence_package(
            session,
            facts=DecisionFacts(
                organization_id=organization_id,
                decision_id=decision.id,
                compliance_review_id=decision.compliance_review_id,
                contract_version_id=decision.contract_version_id,
                status=decision.status,
                supersedes_decision_id=decision.supersedes_decision_id,
                created_at=decision.created_at,
            ),
            actor_id=None,
        )
        await session.commit()
        assert again.id == packages_before[0].id

    packages_after, evidence_after = await _package_rows(db_session_factory, decision.id)
    assert [p.id for p in packages_after] == [p.id for p in packages_before]
    assert len(evidence_after) == len(evidence_before)
    async with db_session_factory() as session:
        audit_after = len(
            await AuditEventRepository(session).list(
                organization_id=organization_id, event_type="evidence.package_created"
            )
        )
    assert audit_after == audit_before


async def test_database_rejects_a_second_package_for_the_same_decision(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    run_contract_extraction_inline,
) -> None:
    mock_openrouter(payload=EVIDENCE_ENVELOPE)
    headers = await register_org_and_login(client, "pkg-unique@example.com")
    supplier = await create_supplier(client, headers, tax_id=TAX_ID)
    contract_version_id = await _upload_contract(client, headers, supplier["id"])
    review = (
        await client.post(
            "/api/compliance/reviews",
            json={"contract_version_id": contract_version_id},
            headers=headers,
        )
    ).json()
    decision = await _decision_for_review(db_session_factory, review["id"])
    [existing], _ = await _package_rows(db_session_factory, decision.id)

    async with db_session_factory() as session:
        session.add(
            EvidencePackage(
                organization_id=existing.organization_id,
                decision_id=decision.id,
                merkle_root="00" * 32,
                evidence_count=0,
            )
        )
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
        else:
            raise AssertionError("a second package for one Decision must be rejected")


async def test_recomputation_matches_the_stored_root_after_a_restart(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
) -> None:
    headers, _, review_id = await _block_review(
        client,
        db_session_factory,
        email="pkg-restart@example.com",
        mock_openrouter=mock_openrouter,
        mock_cnpj_registry=mock_cnpj_registry,
        seed_sanctions_index=seed_sanctions_index,
        rule_yamls=[SANC_001_YAML],
    )
    decision = await _decision_for_review(db_session_factory, review_id)
    [package], _ = await _package_rows(db_session_factory, decision.id)

    # Through the endpoint first.
    response = await client.post(f"/api/evidence-packages/{package.id}/recompute", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["matches"] is True
    assert body["recomputed_merkle_root"] == body["stored_merkle_root"] == package.merkle_root
    assert body["mismatched_evidence_ids"] == []

    # Then from a fresh session with nothing cached.
    recomputed = await _recompute(db_session_factory, package.id)
    assert recomputed.matches is True
    assert recomputed.recomputed_merkle_root == package.merkle_root
    assert recomputed.evidence_count == package.evidence_count


async def test_recompute_never_overwrites_the_stored_root(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    run_contract_extraction_inline,
) -> None:
    mock_openrouter(payload=EVIDENCE_ENVELOPE)
    headers = await register_org_and_login(client, "pkg-readonly@example.com")
    supplier = await create_supplier(client, headers, tax_id=TAX_ID)
    contract_version_id = await _upload_contract(client, headers, supplier["id"])
    review = (
        await client.post(
            "/api/compliance/reviews",
            json={"contract_version_id": contract_version_id},
            headers=headers,
        )
    ).json()
    decision = await _decision_for_review(db_session_factory, review["id"])
    [package], _ = await _package_rows(db_session_factory, decision.id)

    await client.post(f"/api/evidence-packages/{package.id}/recompute", headers=headers)
    [after], _ = await _package_rows(db_session_factory, decision.id)
    assert after.merkle_root == package.merkle_root


async def test_tampering_with_one_persisted_leaf_makes_recompute_mismatch(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
) -> None:
    headers, _, review_id = await _block_review(
        client,
        db_session_factory,
        email="pkg-tamper@example.com",
        mock_openrouter=mock_openrouter,
        mock_cnpj_registry=mock_cnpj_registry,
        seed_sanctions_index=seed_sanctions_index,
        rule_yamls=[SANC_001_YAML],
    )
    decision = await _decision_for_review(db_session_factory, review_id)
    [package], evidence = await _package_rows(db_session_factory, decision.id)
    victim = next(row for row in evidence if row.type == "decision")

    async with db_session_factory() as session:
        row = await session.get(Evidence, victim.id)
        row.payload = {**row.payload, "status": "APPROVE"}  # rewrite history
        await session.commit()

    recomputed = await _recompute(db_session_factory, package.id)
    assert recomputed.matches is False
    assert recomputed.recomputed_merkle_root != package.merkle_root
    assert victim.id in recomputed.mismatched_evidence_ids
    assert recomputed.stored_merkle_root == package.merkle_root

    response = await client.post(f"/api/evidence-packages/{package.id}/recompute", headers=headers)
    assert response.json()["matches"] is False


async def test_superseded_decision_keeps_its_package(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    run_contract_extraction_inline,
) -> None:
    mock_openrouter(payload=EVIDENCE_ENVELOPE)
    headers = await register_org_and_login(client, "pkg-superseded@example.com")
    supplier = await create_supplier(client, headers, tax_id=TAX_ID)
    contract_version_id = await _upload_contract(client, headers, supplier["id"])

    first = (
        await client.post(
            "/api/compliance/reviews",
            json={"contract_version_id": contract_version_id},
            headers=headers,
        )
    ).json()
    first_decision = await _decision_for_review(db_session_factory, first["id"])
    first_package_response = await client.get(
        f"/api/decisions/{first_decision.id}/evidence-package", headers=headers
    )
    assert first_package_response.status_code == 200

    second = (
        await client.post(
            "/api/compliance/reviews",
            json={"contract_version_id": contract_version_id},
            headers=headers,
        )
    ).json()
    second_decision = await _decision_for_review(db_session_factory, second["id"])
    assert second_decision.supersedes_decision_id == first_decision.id

    async with db_session_factory() as session:
        superseded = await session.get(Decision, first_decision.id)
        assert superseded.lifecycle == "SUPERSEDED"

    kept = await client.get(f"/api/decisions/{first_decision.id}/evidence-package", headers=headers)
    assert kept.status_code == 200, kept.text
    assert kept.json()["id"] == first_package_response.json()["id"]
    assert kept.json()["merkle_root"] == first_package_response.json()["merkle_root"]

    second_package = await client.get(
        f"/api/decisions/{second_decision.id}/evidence-package", headers=headers
    )
    assert second_package.json()["id"] != kept.json()["id"]


async def test_package_created_audit_event_is_emitted_once_per_package_with_its_org(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    run_contract_extraction_inline,
) -> None:
    mock_openrouter(payload=EVIDENCE_ENVELOPE)
    email = "pkg-audit@example.com"
    headers = await register_org_and_login(client, email)
    supplier = await create_supplier(client, headers, tax_id=TAX_ID)
    contract_version_id = await _upload_contract(client, headers, supplier["id"])
    review = (
        await client.post(
            "/api/compliance/reviews",
            json={"contract_version_id": contract_version_id},
            headers=headers,
        )
    ).json()
    decision = await _decision_for_review(db_session_factory, review["id"])
    [package], _ = await _package_rows(db_session_factory, decision.id)
    organization_id = await _organization_id(db_session_factory, email)

    async with db_session_factory() as session:
        events = await AuditEventRepository(session).list(
            organization_id=organization_id, event_type="evidence.package_created"
        )
    assert len(events) == 1
    [event] = events
    assert event.organization_id == organization_id
    assert event.payload["evidence_package_id"] == str(package.id)
    assert event.payload["decision_id"] == str(decision.id)
    assert event.payload["merkle_root"] == package.merkle_root
    assert event.payload["evidence_count"] == package.evidence_count
    assert "created_at" in event.payload


async def test_recompute_flags_a_tampered_leaf_even_when_the_root_still_matches(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
) -> None:
    """QA review (2026-10-03): a leaf's stored content_hash can disagree with its payload while the
    recomputed root (built from payloads) still equals the stored root. `matches` must be false."""
    _, _, review_id = await _block_review(
        client,
        db_session_factory,
        email="pkg-hash-tamper@example.com",
        mock_openrouter=mock_openrouter,
        mock_cnpj_registry=mock_cnpj_registry,
        seed_sanctions_index=seed_sanctions_index,
        rule_yamls=[SANC_001_YAML],
    )
    decision = await _decision_for_review(db_session_factory, review_id)
    [package], evidence = await _package_rows(db_session_factory, decision.id)
    victim = evidence[0]

    async with db_session_factory() as session:
        row = await session.get(Evidence, victim.id)
        row.content_hash = "0" * 64
        await session.commit()

    recomputed = await _recompute(db_session_factory, package.id)
    assert recomputed.recomputed_merkle_root == package.merkle_root
    assert victim.id in recomputed.mismatched_evidence_ids
    assert recomputed.matches is False
