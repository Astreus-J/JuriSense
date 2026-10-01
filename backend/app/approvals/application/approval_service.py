"""`ApprovalRequest` routing and the resolution state machine (FEATURE-6.1, APR-001/
APR-003; FEATURE-6.2, APR-002; BR-APR-001/BR-APR-002; docs/03-domain/approvals.md).
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.approvals.application import decision_service, workflow_service
from app.approvals.domain.constants import ApprovalRequestStatus, DecisionStatus
from app.approvals.domain.errors import (
    ApprovalRequestAlreadyResolvedError,
    ApprovalRequestNotFoundError,
    ApproverRoleMismatchError,
    EmptyJustificationError,
    NoApprovalWorkflowConfiguredError,
)
from app.approvals.infrastructure.models import ApprovalRequest
from app.approvals.infrastructure.repositories import (
    ApprovalRequestRepository,
    ApprovalWorkflowRepository,
)
from app.evidence.application.audit_service import emit_audit_event
from app.identity.domain.constants import MembershipStatus
from app.identity.infrastructure.repositories import MembershipRepository


async def create_approval_requests_for_review(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    actor_id: uuid.UUID,
    compliance_review_id: uuid.UUID,
    highest_review_severity: str,
) -> ApprovalRequest:
    """Called from `app.policies.application.compliance_review_service.trigger_review`,
    in the SAME transaction, right after that function's `ComplianceReview`/
    `RuleEvaluation`/`Risk` rows are added to the session and its aggregate outcome is
    `REVIEW` -- this codebase's first write-side (not read-only "evidence port")
    cross-context call; see `trigger_review`'s own docstring for the symmetric note.
    `highest_review_severity` is a plain `str` (never a `Severity` enum instance), computed
    by the caller from its own already-available `RuleEvaluationResult` list -- Approvals &
    Decisions never imports Policy & Compliance's domain types (see
    `tests/approvals/test_boundary_rules.py`).

    Looks up the organization's `ApprovalWorkflow` for `highest_review_severity` and
    instantiates ONLY the first step's `ApprovalRequest` (`pending`, `step_number=1`) --
    later steps are instantiated one at a time as each prior step resolves `approved`
    (`approve_request`, below), never all at once (docs/03-domain/approvals.md "Multi-step
    chains": "steps execute sequentially, not in parallel").

    Raises `NoApprovalWorkflowConfiguredError` if no `ApprovalWorkflow` exists for this
    tier -- shouldn't happen for an organization created after this epic
    (`workflow_service.seed_default_workflows` seeds medium/high/critical at registration),
    but can for pre-epic data or the undocumented `low`-severity-reaches-REVIEW edge case.

    Does not commit -- the caller (`trigger_review`) commits once at the end of its own
    use case.
    """
    workflow = await workflow_service.get_workflow_for_tier(
        session, organization_id=organization_id, trigger_condition=highest_review_severity
    )
    if workflow is None or not workflow.steps:
        raise NoApprovalWorkflowConfiguredError(highest_review_severity)

    request = ApprovalRequest(
        organization_id=organization_id,
        compliance_review_id=compliance_review_id,
        approval_workflow_id=workflow.id,
        approver_role=workflow.steps[0],
        step_number=1,
        status=ApprovalRequestStatus.PENDING.value,
    )
    ApprovalRequestRepository(session).add(request)
    await session.flush()

    await emit_audit_event(
        session,
        event_type="approval.requested",
        actor_id=actor_id,
        organization_id=organization_id,
        payload={
            "approval_request_id": str(request.id),
            "compliance_review_id": str(compliance_review_id),
            "approver_role": request.approver_role,
            "step_number": request.step_number,
            "requested_at": request.requested_at.isoformat(),
        },
    )
    return request


async def _resolve_actor_role(
    session: AsyncSession, *, user_id: uuid.UUID, organization_id: uuid.UUID
) -> str | None:
    """"This user's role in this organization" (BR-APR-001) -- mirrors the pattern
    `app.identity.application.user_service`/`invite_service` already use to keep
    `Membership.role` as the authoritative per-organization role (see e.g.
    `user_service.update_user`'s own `MembershipRepository.get_by_user_and_organization`
    call), rather than inventing a new lookup. Returns `None` if the user has no
    (accepted) `Membership` in this organization at all, OR that membership is no longer
    `active` -- either way treated as a role mismatch by the caller, never a crash.

    Security review (2026-10-01): `get_by_user_and_organization` itself has no `status`
    filter (it's a generic lookup reused elsewhere for cases that want that), so this
    function adds the check explicitly rather than relying on it. Today a revoked
    `Membership` always coincides with `User.is_active=False` (`user_service.
    deactivate_user` sets both together) which already 401s a revoked user long before
    this function ever runs -- but `Membership` exists specifically to support a future
    multi-org-per-user model (domain-model.md) where a user could be revoked from ONE
    organization while remaining active in another; this function must not depend on
    that current, incidental correlation to stay correct once that ships."""
    membership = await MembershipRepository(session).get_by_user_and_organization(
        user_id, organization_id
    )
    if membership is None or membership.status != MembershipStatus.ACTIVE.value:
        return None
    return membership.role


async def get_request(
    session: AsyncSession, *, organization_id: uuid.UUID, request_id: uuid.UUID
) -> ApprovalRequest:
    request = await ApprovalRequestRepository(session).get_by_id_and_organization(
        request_id, organization_id
    )
    if request is None:
        raise ApprovalRequestNotFoundError()
    return request


async def list_requests_for_review(
    session: AsyncSession, *, organization_id: uuid.UUID, compliance_review_id: uuid.UUID
) -> list[ApprovalRequest]:
    """Tenant-ownership of `compliance_review_id` itself is verified by the caller (the
    API route, via `app.policies.application.compliance_review_service.get_review_detail`)
    BEFORE calling this -- mirrors `compliance_review_service.list_reviews_for_contract_version`'s
    own "check first" discipline, just split across the context boundary: this function
    only ever filters by the caller's own `organization_id`, so even without the route's
    upfront check it could never leak another tenant's requests, but the upfront check is
    what turns "a real review id belonging to someone else" into a 404 instead of a
    silently-empty 200 (see `app.approvals.api.routes.list_requests`)."""
    return await ApprovalRequestRepository(session).list_by_review(
        compliance_review_id, organization_id
    )


async def _instantiate_next_step(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    actor_id: uuid.UUID,
    resolved_request: ApprovalRequest,
) -> ApprovalRequest | None:
    """After `resolved_request` resolves `approved`: if the `ApprovalWorkflow` it was
    instantiated from (`approval_workflow_id` -- see that column's design-decision note on
    `ApprovalRequest`) has a step beyond this one, instantiate it (`approval.requested`
    again, `step_number + 1`); returns `None` if `resolved_request` was the chain's last
    step."""
    workflow = await ApprovalWorkflowRepository(session).get_by_id(
        resolved_request.approval_workflow_id
    )
    if workflow is None or resolved_request.step_number >= len(workflow.steps):
        return None

    next_request = ApprovalRequest(
        organization_id=organization_id,
        compliance_review_id=resolved_request.compliance_review_id,
        approval_workflow_id=workflow.id,
        # 1-indexed step_number N used steps[N - 1]; the next step is steps[N] (same
        # index as the old step_number, since Python indexing is 0-based).
        approver_role=workflow.steps[resolved_request.step_number],
        step_number=resolved_request.step_number + 1,
        status=ApprovalRequestStatus.PENDING.value,
    )
    ApprovalRequestRepository(session).add(next_request)
    await session.flush()

    await emit_audit_event(
        session,
        event_type="approval.requested",
        actor_id=actor_id,
        organization_id=organization_id,
        payload={
            "approval_request_id": str(next_request.id),
            "compliance_review_id": str(next_request.compliance_review_id),
            "approver_role": next_request.approver_role,
            "step_number": next_request.step_number,
            "requested_at": next_request.requested_at.isoformat(),
        },
    )
    return next_request


async def approve_request(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    actor_id: uuid.UUID,
    request_id: uuid.UUID,
    justification: str | None = None,
) -> ApprovalRequest:
    """APR-002/BR-APR-001: only a user whose `Membership.role` in this organization
    matches `request.approver_role` may approve. On approval: if more steps remain in the
    workflow, instantiates the next one (`_instantiate_next_step`); if this was the last
    step, creates the review's `Decision` with `status="APPROVE"`
    (`decision_service.create_decision_for_review`) -- this is the only point in the
    codebase where a `REVIEW`-outcome review's `Decision` comes into existence, since
    `trigger_review` itself never creates one for that aggregate outcome (see that
    function's own docstring).

    Commits itself -- this IS the entry use case for `POST
    /approvals/requests/{id}/approve`, same as `trigger_review`/`reject_request`/
    `decision_service.override_decision` commit at the end of theirs.
    """
    request = await get_request(session, organization_id=organization_id, request_id=request_id)

    actor_role = await _resolve_actor_role(
        session, user_id=actor_id, organization_id=organization_id
    )
    if actor_role != request.approver_role:
        raise ApproverRoleMismatchError()

    now = datetime.now(UTC)
    # QA/security review (2026-10-01): the old "load, check status in Python, mutate ORM
    # attributes, flush" sequence raced two concurrent callers against each other (see
    # ApprovalRequestRepository.resolve_if_pending's docstring for the exact scenario).
    # This atomic conditional UPDATE is what actually serializes them now.
    won = await ApprovalRequestRepository(session).resolve_if_pending(
        request.id,
        status=ApprovalRequestStatus.APPROVED.value,
        justification=justification,
        resolved_by=actor_id,
        resolved_at=now,
    )
    if not won:
        raise ApprovalRequestAlreadyResolvedError()
    await session.refresh(request)

    await emit_audit_event(
        session,
        event_type="approval.approved",
        actor_id=actor_id,
        organization_id=organization_id,
        payload={
            "approval_request_id": str(request.id),
            "approved_by": str(actor_id),
            "justification": justification,
            "approved_at": now.isoformat(),
        },
    )

    next_request = await _instantiate_next_step(
        session, organization_id=organization_id, actor_id=actor_id, resolved_request=request
    )
    if next_request is None:
        await decision_service.create_decision_for_review(
            session,
            organization_id=organization_id,
            actor_id=actor_id,
            compliance_review_id=request.compliance_review_id,
            status=DecisionStatus.APPROVE.value,
        )

    await session.commit()
    await session.refresh(request)
    return request


async def reject_request(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    actor_id: uuid.UUID,
    request_id: uuid.UUID,
    justification: str,
) -> ApprovalRequest:
    """APR-002/BR-APR-001 (role-match guard, same as `approve_request`) + BR-APR-002
    (rejection halts the chain): `justification` is mandatory and non-empty here, unlike
    `approve_request`'s optional one (docs/03-domain/approvals.md "On rejection").

    Rejection never instantiates further steps -- the chain halts immediately -- and
    always creates the review's `Decision` with `status="BLOCK"`
    (docs/03-domain/approvals.md: "treated as equivalent in severity to a BLOCK-class
    outcome").

    Commits itself -- this IS the entry use case for `POST
    /approvals/requests/{id}/reject`.
    """
    if not justification or not justification.strip():
        raise EmptyJustificationError()

    request = await get_request(session, organization_id=organization_id, request_id=request_id)

    actor_role = await _resolve_actor_role(
        session, user_id=actor_id, organization_id=organization_id
    )
    if actor_role != request.approver_role:
        raise ApproverRoleMismatchError()

    now = datetime.now(UTC)
    # Same atomic-conditional-UPDATE race fix as approve_request -- see
    # ApprovalRequestRepository.resolve_if_pending's docstring.
    won = await ApprovalRequestRepository(session).resolve_if_pending(
        request.id,
        status=ApprovalRequestStatus.REJECTED.value,
        justification=justification,
        resolved_by=actor_id,
        resolved_at=now,
    )
    if not won:
        raise ApprovalRequestAlreadyResolvedError()
    await session.refresh(request)

    await emit_audit_event(
        session,
        event_type="approval.rejected",
        actor_id=actor_id,
        organization_id=organization_id,
        payload={
            "approval_request_id": str(request.id),
            "rejected_by": str(actor_id),
            "justification": justification,
            "rejected_at": now.isoformat(),
        },
    )

    await decision_service.create_decision_for_review(
        session,
        organization_id=organization_id,
        actor_id=actor_id,
        compliance_review_id=request.compliance_review_id,
        status=DecisionStatus.BLOCK.value,
    )

    await session.commit()
    await session.refresh(request)
    return request
