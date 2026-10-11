"""One-off backfill for Decisions that predate EVD-001: idempotent, one package per Decision, and
every backfilled package recomputes to its stored root (BR-EVD-001)."""

import uuid

import httpx
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.evidence.application import evidence_package_service
from app.evidence.infrastructure.models import Evidence, EvidencePackage
from tests.approvals.conftest import create_supplier, register_org_and_login
from tests.policies.test_compliance_review import EVIDENCE_ENVELOPE, TAX_ID, _upload_contract


async def _delete_as_if_it_predated_evd001(session: AsyncSession, package_ids: list) -> None:
    """#184 added a DB trigger that rejects DELETE on `evidence`/`evidence_packages` -- a real,
    deliberate guarantee for production. These tests still need to construct the one state the
    backfill feature exists for (a Decision that predates EVD-001 and never had a package
    assembled), so they drop the SQLite DELETE trigger first, the same bypass a one-off
    historical-data script would need in the real database."""
    for table in ("evidence", "evidence_packages"):
        await session.execute(text(f"DROP TRIGGER IF EXISTS trg_{table}_append_only_delete"))
    await session.execute(delete(Evidence).where(Evidence.evidence_package_id.in_(package_ids)))
    await session.execute(delete(EvidencePackage).where(EvidencePackage.id.in_(package_ids)))


async def test_backfill_creates_missing_packages_once_and_they_recompute(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    run_contract_extraction_inline,
) -> None:
    mock_openrouter(payload=EVIDENCE_ENVELOPE)
    headers = await register_org_and_login(client, "backfill@example.com")
    supplier = await create_supplier(client, headers, tax_id=TAX_ID)
    contract_version_id = await _upload_contract(client, headers, supplier["id"])
    await client.post(
        "/api/compliance/reviews",
        json={"contract_version_id": contract_version_id},
        headers=headers,
    )

    # Simulate a Decision created before EVD-001: remove its package and leaves.
    async with db_session_factory() as session:
        package_ids = [p.id for p in (await session.execute(select(EvidencePackage))).scalars()]
        await _delete_as_if_it_predated_evd001(session, package_ids)
        await session.commit()

    async with db_session_factory() as session:
        first = await evidence_package_service.backfill_missing_packages(session)
    assert first.considered == 1
    assert first.created == 1
    assert first.already_present == 0
    assert first.failed_decision_ids == ()

    async with db_session_factory() as session:
        second = await evidence_package_service.backfill_missing_packages(session)
    assert second.created == 0
    assert second.already_present == 1

    async with db_session_factory() as session:
        packages = (await session.execute(select(EvidencePackage))).scalars().all()
        assert len(packages) == 1
        recomputed = await evidence_package_service.recompute(
            session, organization_id=packages[0].organization_id, package_id=packages[0].id
        )
    assert recomputed.matches is True
    assert isinstance(recomputed.evidence_package_id, uuid.UUID)


async def test_backfill_records_the_outcome_a_decision_was_created_with_not_its_later_override(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
) -> None:
    """QA review (2026-10-03): override_decision rewrites `status` in place. A backfilled package
    must still record the BLOCK the Decision was created with, not the later APPROVE override."""
    from app.approvals.infrastructure.models import Decision
    from tests.evidence.test_evidence_package import SANC_001_YAML, _block_review

    headers, _, review_id = await _block_review(
        client,
        db_session_factory,
        email="backfill-original@example.com",
        mock_openrouter=mock_openrouter,
        mock_cnpj_registry=mock_cnpj_registry,
        seed_sanctions_index=seed_sanctions_index,
        rule_yamls=[SANC_001_YAML],
    )
    async with db_session_factory() as session:
        decision = (
            await session.execute(
                select(Decision).where(Decision.compliance_review_id == uuid.UUID(review_id))
            )
        ).scalar_one()
        decision_id = decision.id

    override = await client.post(
        f"/api/decisions/{decision_id}/override",
        json={"new_status": "APPROVE", "justification": "Reviewed out of band"},
        headers=headers,
    )
    assert override.status_code == 200, override.text

    async with db_session_factory() as session:
        package_ids = [p.id for p in (await session.execute(select(EvidencePackage))).scalars()]
        await _delete_as_if_it_predated_evd001(session, package_ids)
        await session.commit()

    async with db_session_factory() as session:
        result = await evidence_package_service.backfill_missing_packages(session)
    assert result.created == 1 and result.failed_decision_ids == ()

    async with db_session_factory() as session:
        decision_leaf = (
            await session.execute(select(Evidence).where(Evidence.type == "decision"))
        ).scalar_one()
    assert decision_leaf.payload["status"] == "BLOCK"


async def test_one_failing_decision_does_not_abort_the_backfill_run(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
    monkeypatch,
) -> None:
    """QA review (2026-10-03): an unexpected error for one Decision used to abort the whole run
    with no summary. It must now be recorded against that Decision and the run must finish."""
    from tests.evidence.test_evidence_package import SANC_001_YAML, _block_review

    _, _, review_id = await _block_review(
        client,
        db_session_factory,
        email="backfill-failing@example.com",
        mock_openrouter=mock_openrouter,
        mock_cnpj_registry=mock_cnpj_registry,
        seed_sanctions_index=seed_sanctions_index,
        rule_yamls=[SANC_001_YAML],
    )
    async with db_session_factory() as session:
        package_ids = [p.id for p in (await session.execute(select(EvidencePackage))).scalars()]
        await _delete_as_if_it_predated_evd001(session, package_ids)
        await session.commit()

    async def boom(*args, **kwargs):
        raise RuntimeError("simulated failure for one decision")

    monkeypatch.setattr(evidence_package_service, "assemble_evidence_package", boom)
    async with db_session_factory() as session:
        result = await evidence_package_service.backfill_missing_packages(session)
    assert result.created == 0
    assert len(result.failed_decision_ids) == 1
