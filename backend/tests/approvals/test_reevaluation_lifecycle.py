"""FEATURE-6.5 items 3, 4 and 5 (BR-DEC-002, BR-DEC-004): human overrides are held rather than
replaced; a re-evaluation whose approval chain expired is retried up to a cap, then alerted
once; and a Decision made while no policy existed is flagged when the first policy lands.
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.approvals.application import reevaluation_service
from app.approvals.application.reevaluation_service import reevaluate_stale_decisions
from app.approvals.infrastructure.models import Decision
from app.approvals.infrastructure.repositories import DecisionRepository
from app.core.config import get_settings
from app.policies.infrastructure.models import ComplianceReview
from tests.approvals.conftest import ACTIVE_CNPJ_RESPONSE, register_org_and_login
from tests.approvals.lifecycle_helpers import (
    approve_pending_for,
    audit_events,
    decision_row,
    expire_pending_chain,
    finance_review_chain,
    pending_request_for,
    superseding_review_ids,
)
from tests.approvals.test_reevaluation import (
    _decisions_of,
    _expire_decision,
    _org_id,
    _successor_of,
    _zero_policy_decision,
)
from tests.policies.test_compliance_review import (
    EVIDENCE_ENVELOPE,
    SANC_001_YAML,
    TAX_ID,
    _create_policy_with_rules,
)


async def test_overridden_decision_is_flagged_for_a_human_not_replaced_when_policy_changes(
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

    headers = await register_org_and_login(client, "override-hold@example.com")
    await _zero_policy_decision(client, headers)
    organization_id = await _org_id(db_session_factory, "override-hold@example.com")
    [original] = await _decisions_of(db_session_factory, organization_id)

    justification = "Accepted residual risk per the CFO memo of 2026-09-14"
    overridden = await client.post(
        f"/api/decisions/{original.id}/override",
        json={"new_status": "REVIEW", "justification": justification},
        headers=headers,
    )
    assert overridden.status_code == 200, overridden.text

    await _create_policy_with_rules(
        client, headers, name="Sanctions Policy", rule_yamls=[SANC_001_YAML]
    )

    async with db_session_factory() as session:
        assert await reevaluate_stale_decisions(session) == 0

    events = await audit_events(db_session_factory, organization_id, "compliance.review_required")
    assert len(events) == 1
    assert events[0].payload["reason"] == "override_review_required"
    assert events[0].payload["decision_id"] == str(original.id)
    assert await _successor_of(db_session_factory, original.id) is None

    held = await decision_row(db_session_factory, original.id)
    assert held.lifecycle == "ACTIVE"
    assert held.overridden is True
    assert held.override_justification == justification
    assert held.status == "REVIEW"
    assert held.review_required_reason == "override_review_required"

    # A later sweep does not re-flag or re-emit: the flag is the record that it was reviewed.
    async with db_session_factory() as session:
        assert await reevaluate_stale_decisions(session) == 0
    assert (
        len(await audit_events(db_session_factory, organization_id, "compliance.review_required"))
        == 1
    )


async def test_expired_reevaluation_chain_is_retried_and_its_success_supersedes_the_original(
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
        email="retry-success@example.com",
        mock_openrouter=mock_openrouter,
        mock_cnpj_registry=mock_cnpj_registry,
        seed_sanctions_index=seed_sanctions_index,
    )
    original_id = chain["decision_id"]
    await _expire_decision(db_session_factory, original_id)

    async with db_session_factory() as session:
        assert await reevaluate_stale_decisions(session) == 1
    [first_attempt] = await superseding_review_ids(db_session_factory, original_id)
    await expire_pending_chain(db_session_factory, first_attempt)

    async with db_session_factory() as session:
        assert await reevaluate_stale_decisions(session) == 1
    attempts = await superseding_review_ids(db_session_factory, original_id)
    assert len(attempts) == 2
    [retry] = attempts - {first_attempt}

    review_required = await audit_events(
        db_session_factory, chain["organization_id"], "compliance.review_required"
    )
    assert len(review_required) == 1  # a retry never re-flags the Decision
    assert (
        await audit_events(
            db_session_factory, chain["organization_id"], "compliance.reevaluation_failed"
        )
        == []
    )

    await approve_pending_for(client, chain["legal_headers"], chain["admin_headers"], str(retry))
    successor = await _successor_of(db_session_factory, original_id)
    assert successor is not None
    assert successor.status == "APPROVE"
    assert successor.compliance_review_id == retry
    assert (await decision_row(db_session_factory, original_id)).lifecycle == "SUPERSEDED"


async def test_repeatedly_expired_retries_stop_at_the_cap_with_one_operator_alert(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cap = get_settings().decision_reevaluation_max_attempts
    assert cap == 3  # the documented default this test's cycle count is written against

    chain = await finance_review_chain(
        client,
        db_session_factory,
        email="retry-cap@example.com",
        mock_openrouter=mock_openrouter,
        mock_cnpj_registry=mock_cnpj_registry,
        seed_sanctions_index=seed_sanctions_index,
    )
    original_id = chain["decision_id"]
    organization_id = chain["organization_id"]
    await _expire_decision(db_session_factory, original_id)

    seen: set[uuid.UUID] = set()
    for attempt in range(1, cap + 1):
        async with db_session_factory() as session:
            assert await reevaluate_stale_decisions(session) == 1
        [latest] = await superseding_review_ids(db_session_factory, original_id) - seen
        seen.add(latest)
        assert len(seen) == attempt
        await expire_pending_chain(db_session_factory, latest)

    # Every attempt has now expired. The next sweep is the one that reaches the cap.
    snapshot = await _stale_snapshot(db_session_factory)
    async with db_session_factory() as session:
        assert await reevaluate_stale_decisions(session) == 0

    failures = await audit_events(
        db_session_factory, organization_id, "compliance.reevaluation_failed"
    )
    assert len(failures) == 1
    assert failures[0].payload["decision_id"] == str(original_id)
    assert failures[0].payload["attempts"] == cap
    assert failures[0].payload["last_review_id"] == str(latest)
    assert set(failures[0].payload) == {"decision_id", "attempts", "last_review_id", "failed_at"}
    assert (await decision_row(db_session_factory, original_id)).reevaluation_failed_at is not None

    # Stop retrying: no further review, and no second alert even from a stale snapshot taken
    # before the first alert landed.
    monkeypatch.setattr(DecisionRepository, "list_reevaluation_candidates", _returning(snapshot))
    async with db_session_factory() as session:
        assert await reevaluate_stale_decisions(session) == 0
    monkeypatch.undo()
    async with db_session_factory() as session:
        assert await reevaluate_stale_decisions(session) == 0

    assert len(await superseding_review_ids(db_session_factory, original_id)) == cap
    assert (
        len(
            await audit_events(
                db_session_factory, organization_id, "compliance.reevaluation_failed"
            )
        )
        == 1
    )


async def test_two_overlapping_sweeps_cannot_both_retry_the_same_failed_attempt(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Forced interleaving of the retry claim: both sweeps read the Decision after its first
    attempt expired. The first sweep's compare-and-swap on the generation wins and starts the
    retry; the second sweep, still holding the stale generation, must start nothing."""
    chain = await finance_review_chain(
        client,
        db_session_factory,
        email="retry-race@example.com",
        mock_openrouter=mock_openrouter,
        mock_cnpj_registry=mock_cnpj_registry,
        seed_sanctions_index=seed_sanctions_index,
    )
    original_id = chain["decision_id"]
    organization_id = chain["organization_id"]
    await _expire_decision(db_session_factory, original_id)
    async with db_session_factory() as session:
        assert await reevaluate_stale_decisions(session) == 1
    [first_attempt] = await superseding_review_ids(db_session_factory, original_id)
    await expire_pending_chain(db_session_factory, first_attempt)

    snapshot = await _stale_snapshot(db_session_factory)
    async with db_session_factory() as session:
        assert await reevaluate_stale_decisions(session) == 1  # the winning sweep

    monkeypatch.setattr(DecisionRepository, "list_reevaluation_candidates", _returning(snapshot))
    async with db_session_factory() as session:
        assert await reevaluate_stale_decisions(session) == 0  # the losing sweep

    assert len(await superseding_review_ids(db_session_factory, original_id)) == 2
    assert (
        len(await audit_events(db_session_factory, organization_id, "compliance.review_required"))
        == 1
    )


async def test_an_override_committed_after_the_sweep_read_the_decision_is_never_reevaluated(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Forced interleaving of item 3: the sweep reads the Decision as not overridden and stale,
    then a human override commits before the sweep's flag lands. The flag's compare-and-swap on
    the observed override state must fail, so nothing is re-evaluated over the human decision.
    The next sweep sees the override and holds the Decision for a human."""
    mock_cnpj_registry(data=ACTIVE_CNPJ_RESPONSE)
    await seed_sanctions_index(hit_document=TAX_ID)
    mock_openrouter(payload=EVIDENCE_ENVELOPE)

    headers = await register_org_and_login(client, "override-race@example.com")
    await _zero_policy_decision(client, headers)
    organization_id = await _org_id(db_session_factory, "override-race@example.com")
    [original] = await _decisions_of(db_session_factory, organization_id)
    await _expire_decision(db_session_factory, original.id)

    stale_snapshot = await _stale_snapshot(db_session_factory)
    overridden = await client.post(
        f"/api/decisions/{original.id}/override",
        json={"new_status": "REVIEW", "justification": "Human decision made after the snapshot"},
        headers=headers,
    )
    assert overridden.status_code == 200, overridden.text

    monkeypatch.setattr(
        DecisionRepository, "list_reevaluation_candidates", _returning(stale_snapshot)
    )
    async with db_session_factory() as session:
        assert await reevaluate_stale_decisions(session) == 0
    monkeypatch.undo()

    assert await superseding_review_ids(db_session_factory, original.id) == set()
    assert (
        await audit_events(db_session_factory, organization_id, "compliance.review_required") == []
    )
    held = await decision_row(db_session_factory, original.id)
    assert held.review_required_at is None
    assert held.overridden is True

    async with db_session_factory() as session:
        assert await reevaluate_stale_decisions(session) == 0
    events = await audit_events(db_session_factory, organization_id, "compliance.review_required")
    assert [e.payload["reason"] for e in events] == ["override_review_required"]
    assert await superseding_review_ids(db_session_factory, original.id) == set()


async def test_a_decision_made_with_no_policy_is_flagged_when_the_first_policy_is_published(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
) -> None:
    """Item 5: a review that pooled ZERO policies used to look current forever, because the
    old staleness check only looked at the pooled ids and had nothing to compare. Publishing the
    first policy is now a change in the organization's current policy set."""
    mock_cnpj_registry(data=ACTIVE_CNPJ_RESPONSE)
    await seed_sanctions_index(hit_document=TAX_ID)
    mock_openrouter(payload=EVIDENCE_ENVELOPE)

    headers = await register_org_and_login(client, "zero-policy-stale@example.com")
    _, contract_version_id = await _zero_policy_decision(client, headers)
    organization_id = await _org_id(db_session_factory, "zero-policy-stale@example.com")
    [original] = await _decisions_of(db_session_factory, organization_id)
    assert original.status == "APPROVE"

    async with db_session_factory() as session:
        assert await reevaluate_stale_decisions(session) == 0  # nothing published yet

    policy_id, first_version_id = await _create_policy_with_rules(
        client, headers, name="Sanctions Policy", rule_yamls=[SANC_001_YAML]
    )

    async with db_session_factory() as session:
        assert await reevaluate_stale_decisions(session) == 1
    events = await audit_events(db_session_factory, organization_id, "compliance.review_required")
    assert [e.payload["reason"] for e in events] == ["policy_changed"]

    successor = await _successor_of(db_session_factory, original.id)
    assert successor is not None
    assert successor.status == "BLOCK"  # SANC-001 hits the seeded sanctions entry
    successor_review = await _review_of(db_session_factory, successor.compliance_review_id)
    assert successor_review.policy_version_ids == [first_version_id]
    assert (await decision_row(db_session_factory, original.id)).lifecycle == "SUPERSEDED"

    async with db_session_factory() as session:
        assert await reevaluate_stale_decisions(session) == 0  # now current: not flagged again


async def _review_of(db_session_factory: async_sessionmaker, review_id: uuid.UUID):
    async with db_session_factory() as session:
        return (
            await session.execute(select(ComplianceReview).where(ComplianceReview.id == review_id))
        ).scalar_one()


async def _stale_snapshot(db_session_factory: async_sessionmaker) -> list:
    """What a sweep reads as its candidate list at this moment, detached from the session."""
    async with db_session_factory() as session:
        return await DecisionRepository(session).list_reevaluation_candidates(limit=100)


def _returning(value):
    async def _fake(*_args, **_kwargs):
        return value

    return _fake


def _row_state(decision: Decision) -> dict:
    return {
        "lifecycle": decision.lifecycle,
        "status": decision.status,
        "overridden": decision.overridden,
        "override_justification": decision.override_justification,
        "review_required_at": decision.review_required_at,
        "review_required_reason": decision.review_required_reason,
        "reevaluation_generation": decision.reevaluation_generation,
        "reevaluation_failed_at": decision.reevaluation_failed_at,
    }


async def test_an_overridden_decision_cannot_be_superseded_by_its_pending_reevaluation_chain(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
) -> None:
    """F1(b), the blocker. A Decision is flagged stale and its re-evaluation chain opens; a human
    then overrides the Decision; the chain's approval must NOT silently supersede the override.

    Outcome (asserted below): the approval is refused with 409 before any write. The request
    stays `pending` (the route's session closes without a commit, so its resolution is rolled
    back), the override and the original stay ACTIVE, and no successor is created. A human then
    replaces the override with a manual review, which is allowed."""
    chain = await finance_review_chain(
        client,
        db_session_factory,
        email="override-then-chain@example.com",
        mock_openrouter=mock_openrouter,
        mock_cnpj_registry=mock_cnpj_registry,
        seed_sanctions_index=seed_sanctions_index,
    )
    original_id = chain["decision_id"]
    organization_id = chain["organization_id"]
    await _expire_decision(db_session_factory, original_id)
    async with db_session_factory() as session:
        assert await reevaluate_stale_decisions(session) == 1
    [reeval_review_id] = await superseding_review_ids(db_session_factory, original_id)
    pending = await pending_request_for(client, chain["admin_headers"], str(reeval_review_id))

    justification = "Accepted the residual risk in the CFO memo"
    overridden = await client.post(
        f"/api/decisions/{original_id}/override",
        json={"new_status": "REVIEW", "justification": justification},
        headers=chain["admin_headers"],
    )
    assert overridden.status_code == 200, overridden.text
    held_before = await decision_row(db_session_factory, original_id)
    decisions_created_before = len(
        await audit_events(db_session_factory, organization_id, "decision.created")
    )

    approved = await client.post(
        f"/api/approvals/requests/{pending['id']}/approve",
        json={"justification": "approved in test"},
        headers=chain["legal_headers"],
    )
    assert approved.status_code == 409, approved.text
    assert "manual review" in approved.json()["detail"]
    rejected = await client.post(
        f"/api/approvals/requests/{pending['id']}/reject",
        json={"justification": "rejected in test"},
        headers=chain["legal_headers"],
    )
    assert rejected.status_code == 409, rejected.text

    still_pending = await pending_request_for(client, chain["admin_headers"], str(reeval_review_id))
    assert still_pending["id"] == pending["id"]
    assert still_pending["status"] == "pending"
    held = await decision_row(db_session_factory, original_id)
    assert _row_state(held) == _row_state(held_before)
    assert held.lifecycle == "ACTIVE"
    assert held.overridden is True
    assert held.override_justification == justification
    assert (
        len(await audit_events(db_session_factory, organization_id, "decision.created"))
        == decisions_created_before
    )
    assert await _decision_for_review(db_session_factory, reeval_review_id) is None

    # The automatic path stays closed: the overridden Decision is never retried or re-run.
    async with db_session_factory() as session:
        assert await reevaluate_stale_decisions(session) == 0

    # A human may still replace the override: a manual review's chain supersedes it.
    manual = await client.post(
        "/api/compliance/reviews",
        json={"contract_version_id": str(chain["contract_version_id"])},
        headers=chain["admin_headers"],
    )
    assert manual.status_code == 201, manual.text
    await approve_pending_for(
        client, chain["legal_headers"], chain["admin_headers"], manual.json()["id"]
    )
    replaced = await decision_row(db_session_factory, original_id)
    assert replaced.lifecycle == "SUPERSEDED"
    assert replaced.overridden is True
    assert replaced.override_justification == justification


async def test_an_override_after_the_snapshot_never_fires_the_retry_cap_alert(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """F2: the sweep read the Decision as a retry candidate that reached the attempt cap, then a
    human override committed. The alert must not fire on the overridden Decision: a human owns the
    outcome now, and an automatic-retry alert about it would be wrong."""
    chain = await finance_review_chain(
        client,
        db_session_factory,
        email="alert-after-override@example.com",
        mock_openrouter=mock_openrouter,
        mock_cnpj_registry=mock_cnpj_registry,
        seed_sanctions_index=seed_sanctions_index,
    )
    original_id = chain["decision_id"]
    organization_id = chain["organization_id"]
    await _expire_decision(db_session_factory, original_id)
    async with db_session_factory() as session:
        assert await reevaluate_stale_decisions(session) == 1
    [first_attempt] = await superseding_review_ids(db_session_factory, original_id)
    await expire_pending_chain(db_session_factory, first_attempt)

    [snapshot] = await _stale_snapshot(db_session_factory)
    stale_candidate = reevaluation_service._candidate_of(snapshot)
    assert stale_candidate.overridden is False

    overridden = await client.post(
        f"/api/decisions/{original_id}/override",
        json={"new_status": "REVIEW", "justification": "Human decision after the snapshot"},
        headers=chain["admin_headers"],
    )
    assert overridden.status_code == 200, overridden.text
    # Force the branch under test: the sweep sees the attempt cap reached.
    monkeypatch.setattr(
        reevaluation_service,
        "count_reevaluation_attempts",
        AsyncMock(return_value=get_settings().decision_reevaluation_max_attempts),
    )

    async with db_session_factory() as session:
        assert await reevaluation_service._retry_flagged(session, stale_candidate) is False
        await session.commit()

    held = await decision_row(db_session_factory, original_id)
    assert held.reevaluation_failed_at is None
    assert held.overridden is True
    assert (
        await audit_events(db_session_factory, organization_id, "compliance.reevaluation_failed")
        == []
    )


async def test_a_sweep_rotates_past_checked_decisions_so_a_newer_stale_one_is_reached(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """F3: with a batch of ONE and two effective Decisions, the first sweep checks the older one.
    Ordering by `created_at` alone would pick that same row again on the second sweep and never
    reach the other. Rotation by `last_checked_at` reaches it on the second sweep."""
    mock_cnpj_registry(data=ACTIVE_CNPJ_RESPONSE)
    await seed_sanctions_index(hit_document=TAX_ID)
    mock_openrouter(payload=EVIDENCE_ENVELOPE)

    older_headers = await register_org_and_login(client, "rotation-older@example.com")
    await _zero_policy_decision(client, older_headers)
    newer_headers = await register_org_and_login(client, "rotation-newer@example.com")
    await _zero_policy_decision(client, newer_headers)
    older_org = await _org_id(db_session_factory, "rotation-older@example.com")
    newer_org = await _org_id(db_session_factory, "rotation-newer@example.com")
    [older] = await _decisions_of(db_session_factory, older_org)
    [newer] = await _decisions_of(db_session_factory, newer_org)

    now = datetime.now(UTC)
    async with db_session_factory() as session:
        older_row = await session.get(Decision, older.id)
        older_row.created_at = now - timedelta(days=2)
        newer_row = await session.get(Decision, newer.id)
        newer_row.created_at = now - timedelta(days=1)
        await session.commit()

    settings = get_settings()
    monkeypatch.setattr(
        reevaluation_service,
        "get_settings",
        lambda: settings.model_copy(update={"decision_reevaluation_batch_size": 1}),
    )

    async with db_session_factory() as session:
        assert await reevaluate_stale_decisions(session) == 0
    assert (await decision_row(db_session_factory, older.id)).last_checked_at is not None
    assert (await decision_row(db_session_factory, newer.id)).last_checked_at is None

    async with db_session_factory() as session:
        assert await reevaluate_stale_decisions(session) == 0
    assert (await decision_row(db_session_factory, newer.id)).last_checked_at is not None


async def test_a_reevaluation_that_always_raises_stops_at_the_cap_with_one_alert(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """F4: a deterministic exception used to roll back to the same state every sweep, so it retried
    forever with no alert. Each raise is now recorded in its own committed transaction. At the cap
    the operator alert fires exactly once, and the Decision is never attempted again."""
    mock_openrouter()
    headers = await register_org_and_login(client, "always-raises@example.com")
    await _zero_policy_decision(client, headers)
    organization_id = await _org_id(db_session_factory, "always-raises@example.com")
    [original] = await _decisions_of(db_session_factory, organization_id)
    await _expire_decision(db_session_factory, original.id)

    cap = get_settings().decision_reevaluation_max_attempts
    failing = AsyncMock(side_effect=RuntimeError("deterministic failure"))
    monkeypatch.setattr(reevaluation_service, "execute_review", failing)

    for attempt in range(1, cap + 1):
        async with db_session_factory() as session:
            assert await reevaluate_stale_decisions(session) == 0
        row = await decision_row(db_session_factory, original.id)
        assert row.reevaluation_failure_count == attempt
        assert row.review_required_at is None  # the flag rolled back with the failed unit
        assert row.last_checked_at is not None  # a failing Decision still rotates
        alerts = await audit_events(
            db_session_factory, organization_id, "compliance.reevaluation_failed"
        )
        assert len(alerts) == (1 if attempt == cap else 0)

    assert failing.await_count == cap

    # The cap stops the attempts: later sweeps neither re-run nor alert again.
    async with db_session_factory() as session:
        assert await reevaluate_stale_decisions(session) == 0
    async with db_session_factory() as session:
        assert await reevaluate_stale_decisions(session) == 0
    assert failing.await_count == cap

    [alert] = await audit_events(
        db_session_factory, organization_id, "compliance.reevaluation_failed"
    )
    assert alert.payload["decision_id"] == str(original.id)
    assert alert.payload["attempts"] == cap
    assert alert.payload["last_review_id"] is None
    assert (await decision_row(db_session_factory, original.id)).reevaluation_failed_at is not None


async def _decision_for_review(db_session_factory: async_sessionmaker, review_id: uuid.UUID):
    async with db_session_factory() as session:
        return (
            await session.execute(
                select(Decision).where(Decision.compliance_review_id == review_id)
            )
        ).scalar_one_or_none()
