"""F5 (ADR-003, CLAUDE.md): every repository method that takes an `organization_id` must refuse a
caller that passes another organization's id. Each test calls the method with the WRONG
organization, asserts it touches nothing (returns empty, returns False, or leaves the row
unchanged), and then runs the same call with the right organization as a positive control, so a
method that silently does nothing for everyone cannot pass.
"""

import uuid
from datetime import UTC, datetime

import httpx
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.approvals.application.reevaluation_service import reevaluate_stale_decisions
from app.approvals.infrastructure.repositories import DecisionRepository
from app.policies.infrastructure.repositories import (
    ComplianceReviewRepository,
    PolicyVersionRepository,
)
from tests.approvals.conftest import ACTIVE_CNPJ_RESPONSE, register_org_and_login
from tests.approvals.lifecycle_helpers import decision_row
from tests.approvals.test_reevaluation import (
    _decisions_of,
    _expire_decision,
    _org_id,
    _zero_policy_decision,
)
from tests.policies.test_compliance_review import (
    EVIDENCE_ENVELOPE,
    SANC_001_YAML,
    TAX_ID,
    _create_policy_with_rules,
)


async def _two_tenants(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
) -> dict:
    """Two organizations, each with one effective (APPROVE) Decision on its own ContractVersion."""
    mock_cnpj_registry(data=ACTIVE_CNPJ_RESPONSE)
    await seed_sanctions_index(hit_document=TAX_ID)
    mock_openrouter(payload=EVIDENCE_ENVELOPE)

    tenants = {}
    for label in ("a", "b"):
        email = f"tenant-{label}@example.com"
        headers = await register_org_and_login(client, email)
        _, contract_version_id = await _zero_policy_decision(client, headers)
        organization_id = await _org_id(db_session_factory, email)
        [decision] = await _decisions_of(db_session_factory, organization_id)
        tenants[label] = {
            "headers": headers,
            "organization_id": organization_id,
            "contract_version_id": uuid.UUID(contract_version_id),
            "decision_id": decision.id,
            "review_id": decision.compliance_review_id,
        }
    return tenants


async def test_supersede_if_active_refuses_another_tenants_decision(
    client,
    db_session_factory,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
) -> None:
    t = await _two_tenants(
        client, db_session_factory, mock_openrouter, mock_cnpj_registry, seed_sanctions_index
    )
    a, b = t["a"], t["b"]
    async with db_session_factory() as session:
        assert (
            await DecisionRepository(session).supersede_if_active(
                a["decision_id"], organization_id=b["organization_id"]
            )
            is False
        )
        await session.commit()
    assert (await decision_row(db_session_factory, a["decision_id"])).lifecycle == "ACTIVE"

    async with db_session_factory() as session:
        assert (
            await DecisionRepository(session).supersede_if_active(
                a["decision_id"], organization_id=a["organization_id"]
            )
            is True
        )
        await session.commit()
    assert (await decision_row(db_session_factory, a["decision_id"])).lifecycle == "SUPERSEDED"


async def test_list_active_for_contract_version_is_empty_for_another_tenant(
    client,
    db_session_factory,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
) -> None:
    t = await _two_tenants(
        client, db_session_factory, mock_openrouter, mock_cnpj_registry, seed_sanctions_index
    )
    a, b = t["a"], t["b"]
    async with db_session_factory() as session:
        assert (
            await DecisionRepository(session).list_active_for_contract_version(
                b["organization_id"], a["contract_version_id"]
            )
            == []
        )
    async with db_session_factory() as session:
        found = await DecisionRepository(session).list_active_for_contract_version(
            a["organization_id"], a["contract_version_id"]
        )
    assert [d.id for d in found] == [a["decision_id"]]


async def test_claim_reevaluation_retry_cannot_claim_another_tenants_decision(
    client,
    db_session_factory,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
) -> None:
    t = await _two_tenants(
        client, db_session_factory, mock_openrouter, mock_cnpj_registry, seed_sanctions_index
    )
    a, b = t["a"], t["b"]
    async with db_session_factory() as session:
        assert (
            await DecisionRepository(session).claim_reevaluation_retry(
                a["decision_id"], organization_id=b["organization_id"], observed_generation=0
            )
            is False
        )
        await session.commit()
    assert (await decision_row(db_session_factory, a["decision_id"])).reevaluation_generation == 0

    async with db_session_factory() as session:
        assert (
            await DecisionRepository(session).claim_reevaluation_retry(
                a["decision_id"], organization_id=a["organization_id"], observed_generation=0
            )
            is True
        )
        await session.commit()
    assert (await decision_row(db_session_factory, a["decision_id"])).reevaluation_generation == 1


async def test_mark_reevaluation_failed_cannot_alert_on_another_tenants_decision(
    client,
    db_session_factory,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
) -> None:
    t = await _two_tenants(
        client, db_session_factory, mock_openrouter, mock_cnpj_registry, seed_sanctions_index
    )
    a, b = t["a"], t["b"]
    now = datetime.now(UTC)
    async with db_session_factory() as session:
        assert (
            await DecisionRepository(session).mark_reevaluation_failed_if_unmarked(
                a["decision_id"],
                organization_id=b["organization_id"],
                observed_generation=0,
                failed_at=now,
            )
            is False
        )
        await session.commit()
    assert (await decision_row(db_session_factory, a["decision_id"])).reevaluation_failed_at is None

    async with db_session_factory() as session:
        assert (
            await DecisionRepository(session).mark_reevaluation_failed_if_unmarked(
                a["decision_id"],
                organization_id=a["organization_id"],
                observed_generation=0,
                failed_at=now,
            )
            is True
        )
        await session.commit()
    assert (
        await decision_row(db_session_factory, a["decision_id"])
    ).reevaluation_failed_at is not None


async def test_set_last_reevaluation_review_cannot_write_to_another_tenants_decision(
    client,
    db_session_factory,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
) -> None:
    t = await _two_tenants(
        client, db_session_factory, mock_openrouter, mock_cnpj_registry, seed_sanctions_index
    )
    a, b = t["a"], t["b"]
    async with db_session_factory() as session:
        await DecisionRepository(session).set_last_reevaluation_review(
            a["decision_id"], organization_id=b["organization_id"], review_id=a["review_id"]
        )
        await session.commit()
    assert (
        await decision_row(db_session_factory, a["decision_id"])
    ).last_reevaluation_review_id is None

    async with db_session_factory() as session:
        await DecisionRepository(session).set_last_reevaluation_review(
            a["decision_id"], organization_id=a["organization_id"], review_id=a["review_id"]
        )
        await session.commit()
    assert (
        await decision_row(db_session_factory, a["decision_id"])
    ).last_reevaluation_review_id == a["review_id"]


async def test_count_superseding_ignores_another_tenants_reevaluations(
    client,
    db_session_factory,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
) -> None:
    t = await _two_tenants(
        client, db_session_factory, mock_openrouter, mock_cnpj_registry, seed_sanctions_index
    )
    a, b = t["a"], t["b"]
    await _expire_decision(db_session_factory, a["decision_id"])
    async with db_session_factory() as session:
        assert await reevaluate_stale_decisions(session) >= 1

    async with db_session_factory() as session:
        assert (
            await ComplianceReviewRepository(session).count_superseding(
                a["decision_id"], b["organization_id"]
            )
            == 0
        )
    async with db_session_factory() as session:
        assert (
            await ComplianceReviewRepository(session).count_superseding(
                a["decision_id"], a["organization_id"]
            )
            == 1
        )


async def test_list_current_ids_by_organization_is_empty_for_another_tenant(
    client,
    db_session_factory,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
) -> None:
    mock_cnpj_registry(data=ACTIVE_CNPJ_RESPONSE)
    await seed_sanctions_index(hit_document=TAX_ID)
    mock_openrouter(payload=EVIDENCE_ENVELOPE)
    owner_headers = await register_org_and_login(client, "policy-owner@example.com")
    _, version_id = await _create_policy_with_rules(
        client, owner_headers, name="Owned Policy", rule_yamls=[SANC_001_YAML]
    )
    owner_org = await _org_id(db_session_factory, "policy-owner@example.com")
    await register_org_and_login(client, "policy-stranger@example.com")
    other_org = await _org_id(db_session_factory, "policy-stranger@example.com")

    async with db_session_factory() as session:
        assert (
            await PolicyVersionRepository(session).list_current_ids_by_organization(other_org)
            == set()
        )
    async with db_session_factory() as session:
        assert await PolicyVersionRepository(session).list_current_ids_by_organization(
            owner_org
        ) == {uuid.UUID(version_id)}
