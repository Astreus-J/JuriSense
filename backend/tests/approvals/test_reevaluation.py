"""FEATURE-6.4 / STORY-6.4.1 (DEC-003, BR-DEC-002, BR-DEC-004): stale-Decision re-evaluation.

Exercises `reevaluation_service.reevaluate_stale_decisions` directly against the test
database, the same way `test_sla_expiry.py` exercises its sweep: staleness is manufactured
in the database (an expired `valid_until`, a second analyzed ContractVersion, a second
published PolicyVersion) and the sweep is called as a plain coroutine rather than through
Celery or a real beat schedule.

Race coverage follows `test_concurrency.py`'s style: the exact interleaving a real race
would produce is forced deterministically, since SQLite/StaticPool cannot run genuinely
concurrent transactions.
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.approvals.application import reevaluation_service
from app.approvals.application.reevaluation_service import reevaluate_stale_decisions
from app.approvals.infrastructure.models import Decision
from app.approvals.infrastructure.repositories import DecisionRepository
from app.contracts.infrastructure.models import ContractVersion
from app.evidence.infrastructure.repositories import AuditEventRepository
from app.identity.infrastructure.repositories import UserRepository
from app.policies.infrastructure.models import ComplianceReview
from tests.approvals.conftest import (
    ACTIVE_CNPJ_RESPONSE,
    create_supplier,
    create_user_and_login,
    register_org_and_login,
)
from tests.contracts.conftest import pdf_bytes_with_text
from tests.policies.test_compliance_review import (
    EVIDENCE_ENVELOPE,
    FIN_003_YAML,
    SANC_001_YAML,
    TAX_ID,
    _create_policy_with_rules,
    _upload_contract,
)

# The Decision content fields BR-DEC-002 says a re-evaluation must never change.
_IMMUTABLE_CONTENT_FIELDS = (
    "status",
    "valid_until",
    "overridden",
    "override_justification",
    "compliance_review_id",
    "organization_id",
    "supersedes_decision_id",
)


def _content_of(decision: Decision) -> dict:
    return {field: getattr(decision, field) for field in _IMMUTABLE_CONTENT_FIELDS}


async def _org_id(db_session_factory: async_sessionmaker, email: str) -> uuid.UUID:
    async with db_session_factory() as session:
        user = await UserRepository(session).get_by_email(email)
        return user.organization_id


async def _decisions_of(
    db_session_factory: async_sessionmaker, organization_id: uuid.UUID
) -> list[Decision]:
    async with db_session_factory() as session:
        result = await session.execute(
            select(Decision).where(Decision.organization_id == organization_id)
        )
        return list(result.scalars())


async def _expire_decision(db_session_factory: async_sessionmaker, decision_id: uuid.UUID) -> None:
    async with db_session_factory() as session:
        decision = await session.get(Decision, decision_id)
        decision.valid_until = datetime.now(UTC) - timedelta(days=1)
        await session.commit()


async def _review_required_events(
    db_session_factory: async_sessionmaker, organization_id: uuid.UUID
) -> list:
    async with db_session_factory() as session:
        return await AuditEventRepository(session).list(
            organization_id=organization_id, event_type="compliance.review_required"
        )


async def _successor_of(
    db_session_factory: async_sessionmaker, decision_id: uuid.UUID
) -> Decision | None:
    async with db_session_factory() as session:
        result = await session.execute(
            select(Decision).where(Decision.supersedes_decision_id == decision_id)
        )
        return result.scalars().first()


async def _review_of(db_session_factory: async_sessionmaker, review_id: uuid.UUID):
    async with db_session_factory() as session:
        return await session.get(ComplianceReview, review_id)


async def _zero_policy_decision(client: httpx.AsyncClient, headers: dict) -> tuple[dict, str]:
    """A supplier, a contract, and a review with NO published policies -- which
    aggregates to APPROVE and creates its Decision synchronously, with no approval chain
    involved. Returns (review_json, contract_version_id)."""
    supplier = await create_supplier(client, headers, tax_id=TAX_ID)
    contract_version_id = await _upload_contract(client, headers, supplier["id"])
    response = await client.post(
        "/api/compliance/reviews",
        json={"contract_version_id": contract_version_id},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    assert response.json()["status"] == "APPROVE"
    return response.json(), contract_version_id


async def _upload_version(
    client: httpx.AsyncClient, headers: dict, *, supplier_id: str, contract_id: str
) -> dict:
    """A new negotiation-round ContractVersion of an existing Contract (BR-CON-002)."""
    response = await client.post(
        "/api/contracts/upload",
        files={"file": ("round-2.pdf", pdf_bytes_with_text(), "application/pdf")},
        data={"supplier_id": supplier_id, "contract_id": contract_id},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_expired_decision_is_flagged_reevaluated_and_superseded(
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

    headers = await register_org_and_login(client, "reeval-expired@example.com")
    review, contract_version_id = await _zero_policy_decision(client, headers)
    organization_id = await _org_id(db_session_factory, "reeval-expired@example.com")
    [original] = await _decisions_of(db_session_factory, organization_id)
    original_id = original.id

    await _expire_decision(db_session_factory, original_id)
    # Snapshot after the precondition (expiry), so only the re-evaluation itself is compared.
    [original] = await _decisions_of(db_session_factory, organization_id)
    original_content_before = _content_of(original)

    async with db_session_factory() as session:
        count = await reevaluate_stale_decisions(session)
    assert count == 1

    # The prior Decision: content byte-for-byte unchanged (BR-DEC-002). Only the flag
    # columns -- the flag itself, not a rewrite of the decision -- may differ.
    [original_after] = [
        d for d in await _decisions_of(db_session_factory, organization_id) if d.id == original_id
    ]
    assert _content_of(original_after) == original_content_before
    assert original_after.review_required_reason == "expired"
    assert original_after.review_required_at is not None

    # Exactly one compliance.review_required event, system-initiated, with the catalogued
    # payload shape (docs/03-domain/audit.md).
    events = await _review_required_events(db_session_factory, organization_id)
    assert len(events) == 1
    assert events[0].actor_id is None
    assert set(events[0].payload) == {"decision_id", "reason", "flagged_at"}
    assert events[0].payload["decision_id"] == str(original_id)
    assert events[0].payload["reason"] == "expired"

    # The successor: a NEW Decision on a NEW ComplianceReview, linked back to the original.
    successor = await _successor_of(db_session_factory, original_id)
    assert successor is not None
    assert successor.id != original_id
    assert successor.compliance_review_id != uuid.UUID(review["id"])
    assert successor.status == "APPROVE"
    assert successor.overridden is False
    assert successor.review_required_at is None

    successor_review = await _review_of(db_session_factory, successor.compliance_review_id)
    assert successor_review.supersedes_decision_id == original_id
    # Nothing changed about the contract, so the re-evaluation runs against the same version.
    assert str(successor_review.contract_version_id) == str(contract_version_id)

    # decision.created carries the back-reference too (domain audit catalog).
    async with db_session_factory() as session:
        created = await AuditEventRepository(session).list(
            organization_id=organization_id, event_type="decision.created"
        )
    successor_created = [e for e in created if e.payload["decision_id"] == str(successor.id)]
    assert len(successor_created) == 1
    assert successor_created[0].payload["supersedes_decision_id"] == str(original_id)


async def test_flagging_a_decision_never_gives_it_a_second_compliance_review_row(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
) -> None:
    """The unique constraint on decisions.compliance_review_id stays: a successor always
    belongs to a NEW ComplianceReview, so it never collides. A second Decision on the SAME
    review is still refused by the database."""
    mock_cnpj_registry(data=ACTIVE_CNPJ_RESPONSE)
    await seed_sanctions_index(hit_document=TAX_ID)
    mock_openrouter(payload=EVIDENCE_ENVELOPE)

    headers = await register_org_and_login(client, "reeval-unique@example.com")
    await _zero_policy_decision(client, headers)
    organization_id = await _org_id(db_session_factory, "reeval-unique@example.com")
    [original] = await _decisions_of(db_session_factory, organization_id)
    await _expire_decision(db_session_factory, original.id)

    async with db_session_factory() as session:
        await reevaluate_stale_decisions(session)
    successor = await _successor_of(db_session_factory, original.id)
    assert successor.compliance_review_id != original.compliance_review_id

    async with db_session_factory() as session:
        session.add(
            Decision(
                organization_id=organization_id,
                compliance_review_id=original.compliance_review_id,
                status="BLOCK",
                valid_until=datetime.now(UTC) + timedelta(days=1),
            )
        )
        with pytest.raises(IntegrityError):
            await session.flush()
        await session.rollback()


async def test_contract_changed_flags_and_reevaluates_against_the_newer_version(
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

    headers = await register_org_and_login(client, "reeval-contract@example.com")
    supplier = await create_supplier(client, headers, tax_id=TAX_ID)
    v1_id = await _upload_contract(client, headers, supplier["id"])
    await client.post(
        "/api/compliance/reviews", json={"contract_version_id": v1_id}, headers=headers
    )
    organization_id = await _org_id(db_session_factory, "reeval-contract@example.com")
    [original] = await _decisions_of(db_session_factory, organization_id)

    # Nothing stale yet: the sweep must leave a current Decision alone.
    async with db_session_factory() as session:
        assert await reevaluate_stale_decisions(session) == 0

    v1_row = await _version_row(db_session_factory, uuid.UUID(v1_id))
    # A second negotiation round of the same Contract, analyzed by the inline extraction.
    v2 = await _upload_version(
        client, headers, supplier_id=supplier["id"], contract_id=str(v1_row.contract_id)
    )
    assert v2["version_number"] == 2
    # The upload response predates inline extraction, so the analyzed status is read back.
    assert (await _version_row(db_session_factory, uuid.UUID(v2["id"]))).status == "analyzed"

    async with db_session_factory() as session:
        count = await reevaluate_stale_decisions(session)
    assert count == 1

    events = await _review_required_events(db_session_factory, organization_id)
    assert [e.payload["reason"] for e in events] == ["contract_changed"]

    successor = await _successor_of(db_session_factory, original.id)
    assert successor is not None
    successor_review = await _review_of(db_session_factory, successor.compliance_review_id)
    assert str(successor_review.contract_version_id) == v2["id"]
    assert successor_review.supersedes_decision_id == original.id


async def _version_row(db_session_factory: async_sessionmaker, version_id: uuid.UUID):
    async with db_session_factory() as session:
        return await session.get(ContractVersion, version_id)


async def test_policy_changed_flags_and_reevaluates_when_a_pooled_policy_is_republished(
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

    headers = await register_org_and_login(client, "reeval-policy@example.com")
    supplier = await create_supplier(client, headers, tax_id=TAX_ID)
    contract_version_id = await _upload_contract(client, headers, supplier["id"])
    policy_id, v1_id = await _create_policy_with_rules(
        client, headers, name="Vendor Policy", rule_yamls=[SANC_001_YAML]
    )
    review = (
        await client.post(
            "/api/compliance/reviews",
            json={"contract_version_id": contract_version_id},
            headers=headers,
        )
    ).json()
    assert review["status"] == "BLOCK"
    organization_id = await _org_id(db_session_factory, "reeval-policy@example.com")
    [original] = await _decisions_of(db_session_factory, organization_id)

    # Publish a newer version of the same policy: v1 is no longer its current version.
    draft = await client.post(f"/api/policies/{policy_id}/versions", headers=headers)
    assert draft.status_code == 201, draft.text
    published = await client.post(
        f"/api/policies/{policy_id}/versions/{draft.json()['id']}/publish", headers=headers
    )
    assert published.status_code == 200, published.text

    async with db_session_factory() as session:
        count = await reevaluate_stale_decisions(session)
    assert count == 1

    events = await _review_required_events(db_session_factory, organization_id)
    assert [e.payload["reason"] for e in events] == ["policy_changed"]

    successor = await _successor_of(db_session_factory, original.id)
    assert successor is not None
    assert successor.status == "BLOCK"
    successor_review = await _review_of(db_session_factory, successor.compliance_review_id)
    assert draft.json()["id"] in successor_review.policy_version_ids
    assert v1_id not in successor_review.policy_version_ids
    assert successor_review.supersedes_decision_id == original.id


async def test_sweep_is_idempotent_one_flag_one_event_one_successor(
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

    headers = await register_org_and_login(client, "reeval-idem@example.com")
    await _zero_policy_decision(client, headers)
    organization_id = await _org_id(db_session_factory, "reeval-idem@example.com")
    [original] = await _decisions_of(db_session_factory, organization_id)
    await _expire_decision(db_session_factory, original.id)

    async with db_session_factory() as session:
        first = await reevaluate_stale_decisions(session)
    async with db_session_factory() as session:
        second = await reevaluate_stale_decisions(session)

    assert first == 1
    assert second == 0
    assert len(await _review_required_events(db_session_factory, organization_id)) == 1
    decisions = await _decisions_of(db_session_factory, organization_id)
    assert len(decisions) == 2
    assert len([d for d in decisions if d.supersedes_decision_id == original.id]) == 1


async def test_already_flagged_decision_loses_the_race_and_is_not_reevaluated(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Forced interleaving: this sweep reads the Decision as unflagged, then an overlapping
    sweep flags it before this one's own conditional UPDATE lands. This sweep's UPDATE
    must match zero rows, so it neither re-evaluates nor emits a second event -- the
    overlapping sweep alone owns the flagged Decision."""
    mock_cnpj_registry(data=ACTIVE_CNPJ_RESPONSE)
    await seed_sanctions_index(hit_document=TAX_ID)
    mock_openrouter(payload=EVIDENCE_ENVELOPE)

    headers = await register_org_and_login(client, "reeval-race@example.com")
    await _zero_policy_decision(client, headers)
    organization_id = await _org_id(db_session_factory, "reeval-race@example.com")
    [original] = await _decisions_of(db_session_factory, organization_id)
    await _expire_decision(db_session_factory, original.id)

    # This sweep's candidate read happens BEFORE the other caller's flag lands.
    async with db_session_factory() as session:
        stale_snapshot = await DecisionRepository(session).list_reevaluation_candidates(limit=100)
    assert [d.id for d in stale_snapshot] == [original.id]

    # The overlapping caller wins the flag.
    async with db_session_factory() as session:
        won_first = await DecisionRepository(session).flag_for_review_if_unflagged(
            original.id,
            organization_id=organization_id,
            reason="expired",
            flagged_at=datetime.now(UTC),
        )
        await session.commit()
    assert won_first is True

    monkeypatch.setattr(
        DecisionRepository, "list_reevaluation_candidates", AsyncMock(return_value=stale_snapshot)
    )
    spy_execute_review = AsyncMock()
    monkeypatch.setattr(reevaluation_service, "execute_review", spy_execute_review)

    async with db_session_factory() as session:
        count = await reevaluate_stale_decisions(session)

    assert count == 0
    spy_execute_review.assert_not_awaited()
    assert await _review_required_events(db_session_factory, organization_id) == []
    assert await _successor_of(db_session_factory, original.id) is None
    [flagged] = [
        d for d in await _decisions_of(db_session_factory, organization_id) if d.id == original.id
    ]
    assert flagged.review_required_reason == "expired"


async def test_review_outcome_successor_waits_for_its_approval_chain_then_links_back(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
) -> None:
    """Exercises the DEFERRED path: a re-evaluation whose aggregate is REVIEW creates an
    approval chain and no Decision. The successor Decision appears only once the chain
    resolves, and then carries `supersedes_decision_id` via `approval_service`, which reads
    it from the review row."""
    mock_cnpj_registry(data=ACTIVE_CNPJ_RESPONSE)
    await seed_sanctions_index(hit_document=TAX_ID)
    mock_openrouter(payload=EVIDENCE_ENVELOPE)

    admin_headers = await register_org_and_login(client, "reeval-review@example.com")
    supplier = await create_supplier(client, admin_headers, tax_id=TAX_ID)
    contract_version_id = await _upload_contract(client, admin_headers, supplier["id"])
    await _create_policy_with_rules(
        client, admin_headers, name="Vendor Policy", rule_yamls=[FIN_003_YAML]
    )
    legal_headers = await create_user_and_login(
        client, admin_headers, email="reeval-legal@example.com", role="legal"
    )
    review = (
        await client.post(
            "/api/compliance/reviews",
            json={"contract_version_id": contract_version_id},
            headers=admin_headers,
        )
    ).json()
    assert review["status"] == "REVIEW"

    async def _requests_for(review_id: str) -> list[dict]:
        return (
            await client.get(
                "/api/approvals/requests",
                params={"compliance_review_id": review_id},
                headers=admin_headers,
            )
        ).json()

    original_request = (await _requests_for(review["id"]))[0]
    approved = await client.post(
        f"/api/approvals/requests/{original_request['id']}/approve",
        json={"justification": "Initial approval"},
        headers=legal_headers,
    )
    assert approved.status_code == 200, approved.text

    organization_id = await _org_id(db_session_factory, "reeval-review@example.com")
    [original] = await _decisions_of(db_session_factory, organization_id)
    assert original.status == "APPROVE"

    await _expire_decision(db_session_factory, original.id)
    [original] = await _decisions_of(db_session_factory, organization_id)
    original_content_before = _content_of(original)
    async with db_session_factory() as session:
        assert await reevaluate_stale_decisions(session) == 1

    # The re-evaluation is itself REVIEW: a pending chain, and NO successor Decision yet.
    async with db_session_factory() as session:
        successor_review = (
            await session.execute(
                select(ComplianceReview).where(
                    ComplianceReview.supersedes_decision_id == original.id
                )
            )
        ).scalar_one()
    assert successor_review.status == "REVIEW"
    assert await _successor_of(db_session_factory, original.id) is None

    [pending] = await _requests_for(str(successor_review.id))
    assert pending["status"] == "pending"
    assert pending["approver_role"] == "legal"

    [original_after] = [
        d for d in await _decisions_of(db_session_factory, organization_id) if d.id == original.id
    ]
    assert _content_of(original_after) == original_content_before

    resolved = await client.post(
        f"/api/approvals/requests/{pending['id']}/approve",
        json={"justification": "Re-approved after expiry"},
        headers=legal_headers,
    )
    assert resolved.status_code == 200, resolved.text

    successor = await _successor_of(db_session_factory, original.id)
    assert successor is not None
    assert successor.status == "APPROVE"
    assert successor.compliance_review_id == successor_review.id
    assert successor.supersedes_decision_id == original.id
    assert _content_of(original_after) == original_content_before


async def test_stale_decision_in_one_organization_never_touches_another(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
) -> None:
    """Tenant isolation: the sweep is platform-wide, but only the stale organization's
    Decision may be flagged, re-evaluated, or produce an event."""
    mock_cnpj_registry(data=ACTIVE_CNPJ_RESPONSE)
    await seed_sanctions_index(hit_document=TAX_ID)
    mock_openrouter(payload=EVIDENCE_ENVELOPE)

    headers_a = await register_org_and_login(client, "reeval-tenant-a@example.com")
    headers_b = await register_org_and_login(client, "reeval-tenant-b@example.com")
    await _zero_policy_decision(client, headers_a)
    await _zero_policy_decision(client, headers_b)
    org_a = await _org_id(db_session_factory, "reeval-tenant-a@example.com")
    org_b = await _org_id(db_session_factory, "reeval-tenant-b@example.com")
    [decision_a] = await _decisions_of(db_session_factory, org_a)
    [decision_b] = await _decisions_of(db_session_factory, org_b)

    await _expire_decision(db_session_factory, decision_a.id)

    async with db_session_factory() as session:
        assert await reevaluate_stale_decisions(session) == 1

    assert await _successor_of(db_session_factory, decision_a.id) is not None
    assert await _successor_of(db_session_factory, decision_b.id) is None
    assert len(await _review_required_events(db_session_factory, org_a)) == 1
    assert await _review_required_events(db_session_factory, org_b) == []
    [untouched_b] = await _decisions_of(db_session_factory, org_b)
    assert untouched_b.review_required_at is None
    assert len(await _decisions_of(db_session_factory, org_b)) == 1


async def test_a_failed_reevaluation_rolls_its_flag_back_so_the_next_sweep_retries(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A Decision whose re-evaluation blows up must not be left flagged with no successor:
    the flag is part of the same unit of work, so it rolls back and the next run retries."""
    mock_cnpj_registry(data=ACTIVE_CNPJ_RESPONSE)
    await seed_sanctions_index(hit_document=TAX_ID)
    mock_openrouter(payload=EVIDENCE_ENVELOPE)

    headers = await register_org_and_login(client, "reeval-rollback@example.com")
    await _zero_policy_decision(client, headers)
    organization_id = await _org_id(db_session_factory, "reeval-rollback@example.com")
    [original] = await _decisions_of(db_session_factory, organization_id)
    await _expire_decision(db_session_factory, original.id)

    real_execute_review = reevaluation_service.execute_review
    monkeypatch.setattr(
        reevaluation_service, "execute_review", AsyncMock(side_effect=RuntimeError("boom"))
    )
    async with db_session_factory() as session:
        assert await reevaluate_stale_decisions(session) == 0

    [still_unflagged] = [
        d for d in await _decisions_of(db_session_factory, organization_id) if d.id == original.id
    ]
    assert still_unflagged.review_required_at is None
    assert await _review_required_events(db_session_factory, organization_id) == []

    monkeypatch.setattr(reevaluation_service, "execute_review", real_execute_review)
    async with db_session_factory() as session:
        assert await reevaluate_stale_decisions(session) == 1
    assert await _successor_of(db_session_factory, original.id) is not None


def test_reevaluation_task_is_registered_and_scheduled_by_beat() -> None:
    from app.approvals.infrastructure import tasks  # noqa: F401 -- registers the task
    from app.core.celery_app import celery_app
    from app.core.config import get_settings

    assert "approvals.reevaluate_stale_decisions" in celery_app.tasks
    entry = celery_app.conf.beat_schedule["approvals-reevaluate-stale-decisions"]
    assert entry["task"] == "approvals.reevaluate_stale_decisions"
    assert entry["schedule"] == get_settings().decision_reevaluation_interval_seconds


async def test_candidate_snapshot_loads_nothing_already_superseded_or_flagged(
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

    headers = await register_org_and_login(client, "reeval-filter@example.com")
    await _zero_policy_decision(client, headers)
    organization_id = await _org_id(db_session_factory, "reeval-filter@example.com")
    [original] = await _decisions_of(db_session_factory, organization_id)
    await _expire_decision(db_session_factory, original.id)
    async with db_session_factory() as session:
        await reevaluate_stale_decisions(session)

    async with db_session_factory() as session:
        candidate_ids = [
            d.id for d in await DecisionRepository(session).list_reevaluation_candidates(limit=100)
        ]
    successor = await _successor_of(db_session_factory, original.id)
    # The original is flagged, the successor is current: neither may be a candidate.
    assert original.id not in candidate_ids
    assert successor.id in candidate_ids


async def test_flag_is_refused_for_another_organizations_decision(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
) -> None:
    """Security review (2026-10-03): the flag UPDATE is tenant-scoped, so a caller passing
    the wrong organization id can never flag another tenant's Decision (ADR-003)."""
    mock_cnpj_registry(data=ACTIVE_CNPJ_RESPONSE)
    await seed_sanctions_index(hit_document=TAX_ID)
    mock_openrouter(payload=EVIDENCE_ENVELOPE)

    headers = await register_org_and_login(client, "reeval-xtenant-flag@example.com")
    await _zero_policy_decision(client, headers)
    organization_id = await _org_id(db_session_factory, "reeval-xtenant-flag@example.com")
    [original] = await _decisions_of(db_session_factory, organization_id)

    async with db_session_factory() as session:
        won = await DecisionRepository(session).flag_for_review_if_unflagged(
            original.id,
            organization_id=uuid.uuid4(),
            reason="expired",
            flagged_at=datetime.now(UTC),
        )
        await session.commit()
    assert won is False

    [still] = await _decisions_of(db_session_factory, organization_id)
    assert still.review_required_at is None


async def test_candidate_read_is_capped_at_the_batch_size(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
) -> None:
    """Security review (2026-10-03, H1): one tenant with many live Decisions must not be
    able to make a single sweep run unbounded. The candidate read honours the batch limit,
    oldest first, so the rest of the backlog drains on later runs."""
    mock_cnpj_registry(data=ACTIVE_CNPJ_RESPONSE)
    await seed_sanctions_index(hit_document=TAX_ID)
    mock_openrouter(payload=EVIDENCE_ENVELOPE)

    headers = await register_org_and_login(client, "reeval-cap@example.com")
    await _zero_policy_decision(client, headers)
    organization_id = await _org_id(db_session_factory, "reeval-cap@example.com")
    [original] = await _decisions_of(db_session_factory, organization_id)
    await _expire_decision(db_session_factory, original.id)

    async with db_session_factory() as session:
        capped = await DecisionRepository(session).list_reevaluation_candidates(limit=0)
    assert capped == []

    async with db_session_factory() as session:
        one = await DecisionRepository(session).list_reevaluation_candidates(limit=1)
    assert [d.id for d in one] == [original.id]


async def test_superseding_a_decision_from_another_organization_is_refused(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
) -> None:
    """Security review (2026-10-03, M1): a supersedes link must never point at another
    organization's Decision, or that Decision would be silently excluded from the sweep."""
    from app.approvals.domain.errors import DecisionNotFoundError as ApprovalsDecisionNotFound
    from app.policies.application.compliance_review_service import execute_review

    mock_cnpj_registry(data=ACTIVE_CNPJ_RESPONSE)
    await seed_sanctions_index(hit_document=TAX_ID)
    mock_openrouter(payload=EVIDENCE_ENVELOPE)

    owner_headers = await register_org_and_login(client, "reeval-owner-super@example.com")
    await _zero_policy_decision(client, owner_headers)
    owner_org = await _org_id(db_session_factory, "reeval-owner-super@example.com")
    [foreign_decision] = await _decisions_of(db_session_factory, owner_org)

    attacker_headers = await register_org_and_login(client, "reeval-attacker-super@example.com")
    attacker_org = await _org_id(db_session_factory, "reeval-attacker-super@example.com")
    supplier = await create_supplier(client, attacker_headers, tax_id=TAX_ID)
    contract_version_id = uuid.UUID(
        await _upload_contract(client, attacker_headers, supplier["id"])
    )

    async with db_session_factory() as session:
        with pytest.raises(ApprovalsDecisionNotFound):
            await execute_review(
                session,
                organization_id=attacker_org,
                actor_id=None,
                contract_version_id=contract_version_id,
                supersedes_decision_id=foreign_decision.id,
            )
