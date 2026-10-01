"""QA/security review (2026-10-01): regression tests for the concurrent-write races both
reviews independently found in the original `approve_request`/`reject_request`/
`expire_stale_approval_requests` implementation (load-then-mutate-then-commit, with no
row lock and no conditional `WHERE status = 'pending'` guard). True concurrency can't be
reproduced hermetically (SQLite/StaticPool doesn't support genuinely concurrent
transactions -- same limitation noted throughout this codebase's other concurrency
tests); each test here instead deterministically forces the exact interleaving a real
race would produce, by calling the repository's atomic methods directly in the specific
order two simultaneous callers would land in.
"""

import uuid
from datetime import UTC, datetime

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.approvals.application.approval_service import approve_request
from app.approvals.application.decision_service import create_decision_for_review
from app.approvals.domain.constants import ApprovalRequestStatus, DecisionStatus
from app.approvals.domain.errors import ApproverRoleMismatchError, DecisionAlreadyExistsError
from app.approvals.infrastructure.models import ApprovalRequest
from app.approvals.infrastructure.repositories import ApprovalRequestRepository
from app.identity.domain.constants import MembershipStatus
from app.identity.infrastructure.models import Membership
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
    TAX_ID,
    _create_policy_with_rules,
    _upload_contract,
)


async def _review_with_pending_request(client: httpx.AsyncClient, headers: dict) -> dict:
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


async def test_resolve_if_pending_only_lets_one_of_two_racing_callers_win(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
) -> None:
    """The core fix: `ApprovalRequestRepository.resolve_if_pending`'s atomic conditional
    `UPDATE` is what the old load-then-mutate-then-commit sequence lacked. Simulates two
    "simultaneous" `approve_request` calls on the exact same request by invoking the
    repository method twice in immediate succession, with no refresh between them --
    exactly the interleaving a real race would produce (both readers see `pending`, only
    one writer's conditional `UPDATE` actually matches a row)."""
    mock_cnpj_registry(data=ACTIVE_CNPJ_RESPONSE)
    await seed_sanctions_index(hit_document=TAX_ID)
    mock_openrouter(payload=EVIDENCE_ENVELOPE)

    headers = await register_org_and_login(client, "race-resolve@example.com")
    review = await _review_with_pending_request(client, headers)
    request_id = uuid.UUID(
        (
            await client.get(
                "/api/approvals/requests",
                params={"compliance_review_id": review["id"]},
                headers=headers,
            )
        ).json()[0]["id"]
    )

    async with db_session_factory() as session:
        repository = ApprovalRequestRepository(session)
        first_wins = await repository.resolve_if_pending(
            request_id,
            status=ApprovalRequestStatus.APPROVED.value,
            justification="first caller",
            resolved_by=uuid.uuid4(),
            resolved_at=datetime.now(UTC),
        )
        second_wins = await repository.resolve_if_pending(
            request_id,
            status=ApprovalRequestStatus.REJECTED.value,
            justification="second caller -- should lose the race",
            resolved_by=uuid.uuid4(),
            resolved_at=datetime.now(UTC),
        )
        await session.commit()

    assert first_wins is True
    assert second_wins is False

    async with db_session_factory() as session:
        loaded = await session.get(ApprovalRequest, request_id)
        # The second (losing) caller's values never landed -- the row reflects only the
        # winner, never a half-applied mix of both callers' writes.
        assert loaded.status == "approved"
        assert loaded.justification == "first caller"


async def test_sla_sweep_never_clobbers_a_human_resolution_that_won_first(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
) -> None:
    """The exact scenario both the QA and security reviews independently identified: a
    human resolves a request, and the SLA-expiry sweep's own candidate list was computed
    from a snapshot taken before that resolution landed. Forces this deterministically by
    resolving the request first, then calling the sweep's atomic transition on the same
    (now-already-resolved) row -- it must do nothing, not silently overwrite the human's
    resolution back to `expired`."""
    mock_cnpj_registry(data=ACTIVE_CNPJ_RESPONSE)
    await seed_sanctions_index(hit_document=TAX_ID)
    mock_openrouter(payload=EVIDENCE_ENVELOPE)

    admin_headers = await register_org_and_login(client, "race-sla-admin@example.com")
    legal_headers = await create_user_and_login(
        client, admin_headers, email="race-sla-legal@example.com", role="legal"
    )
    review = await _review_with_pending_request(client, admin_headers)
    request_id = (
        await client.get(
            "/api/approvals/requests",
            params={"compliance_review_id": review["id"]},
            headers=admin_headers,
        )
    ).json()[0]["id"]

    # The human resolves it first (simulating that this happened right before the SLA
    # sweep's own transition attempt for the same, now-already-resolved, row).
    resolved = await client.post(
        f"/api/approvals/requests/{request_id}/approve",
        json={"justification": "Resolved just in time"},
        headers=legal_headers,
    )
    assert resolved.status_code == 200, resolved.text

    async with db_session_factory() as session:
        won = await ApprovalRequestRepository(session).expire_pending_if_pending(
            uuid.UUID(request_id)
        )
        await session.commit()
    assert won is False  # the sweep must not have transitioned an already-resolved row

    detail = await client.get(f"/api/approvals/requests/{request_id}", headers=admin_headers)
    body = detail.json()
    # Still reflects the human's resolution -- not silently flipped to "expired".
    assert body["status"] == "approved"
    assert body["justification"] == "Resolved just in time"


async def test_second_decision_for_the_same_review_is_a_clean_conflict_not_a_duplicate_row(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
) -> None:
    """Defense-in-depth backstop: `decisions.uq_decisions_one_per_compliance_review`
    (added alongside the `resolve_if_pending` fix) must turn a second
    `create_decision_for_review` call for the same review into a clean
    `DecisionAlreadyExistsError`, never a second, contradictory `Decision` row sitting
    silently alongside the first."""
    mock_cnpj_registry(data=ACTIVE_CNPJ_RESPONSE)
    await seed_sanctions_index(hit_document=TAX_ID)
    mock_openrouter(payload=EVIDENCE_ENVELOPE)

    headers = await register_org_and_login(client, "race-decision@example.com")
    review = await _review_with_pending_request(client, headers)
    review_id = uuid.UUID(review["id"])

    async with db_session_factory() as session:
        user = await UserRepository(session).get_by_email("race-decision@example.com")
        organization_id = user.organization_id

    async with db_session_factory() as session:
        await create_decision_for_review(
            session,
            organization_id=organization_id,
            actor_id=None,
            compliance_review_id=review_id,
            status=DecisionStatus.APPROVE.value,
        )
        await session.commit()

    async with db_session_factory() as session:
        with pytest.raises(DecisionAlreadyExistsError):
            await create_decision_for_review(
                session,
                organization_id=organization_id,
                actor_id=None,
                compliance_review_id=review_id,
                status=DecisionStatus.BLOCK.value,
            )


async def test_revoked_membership_cannot_resolve_an_approval_request(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
) -> None:
    """Security review (2026-10-01): `_resolve_actor_role` must not grant resolution
    rights based on a `Membership` row whose `status` is no longer `active`, even though
    today a revoked membership always coincides with a globally-inactive `User` that
    would already be refused earlier in the stack (`get_current_user`). This exercises
    `_resolve_actor_role`'s own defense-in-depth directly, independent of that upstream
    coincidence, by hand-crafting a `REVOKED` membership for an otherwise-active user."""
    mock_cnpj_registry(data=ACTIVE_CNPJ_RESPONSE)
    await seed_sanctions_index(hit_document=TAX_ID)
    mock_openrouter(payload=EVIDENCE_ENVELOPE)

    admin_headers = await register_org_and_login(client, "race-revoked-admin@example.com")
    await create_user_and_login(
        client, admin_headers, email="race-revoked-legal@example.com", role="legal"
    )
    review = await _review_with_pending_request(client, admin_headers)
    request_id = uuid.UUID(
        (
            await client.get(
                "/api/approvals/requests",
                params={"compliance_review_id": review["id"]},
                headers=admin_headers,
            )
        ).json()[0]["id"]
    )

    # Force the revoke the same way user_service.deactivate_user does to Membership.status
    # alone, deliberately WITHOUT touching User.is_active -- so this exercises
    # _resolve_actor_role's own defense-in-depth directly, independent of the unrelated,
    # already-existing get_current_user gate that would otherwise mask it.
    async with db_session_factory() as session:
        legal_user = await UserRepository(session).get_by_email("race-revoked-legal@example.com")
        organization_id = legal_user.organization_id
        legal_user_id = legal_user.id
        membership = (
            await session.execute(
                select(Membership).where(
                    Membership.user_id == legal_user_id,
                    Membership.organization_id == organization_id,
                )
            )
        ).scalar_one()
        membership.status = MembershipStatus.REVOKED.value
        await session.commit()

    async with db_session_factory() as session:
        with pytest.raises(ApproverRoleMismatchError):
            await approve_request(
                session,
                organization_id=organization_id,
                actor_id=legal_user_id,
                request_id=request_id,
                justification="should be refused",
            )
