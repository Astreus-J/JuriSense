"""Decision assembly and manual override (FEATURE-6.3, DEC-001/DEC-002; BR-DEC-001/
BR-DEC-003; docs/03-domain/domain-model.md "Decision").
"""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.approvals.domain.errors import DecisionNotFoundError, EmptyJustificationError
from app.approvals.infrastructure.models import Decision
from app.approvals.infrastructure.repositories import DecisionRepository
from app.core.config import get_settings
from app.evidence.application.audit_service import emit_audit_event


async def create_decision_for_review(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    actor_id: uuid.UUID | None,
    compliance_review_id: uuid.UUID,
    status: str,
) -> Decision:
    """Creates the final, packaged `Decision` for one `ComplianceReview` (DEC-001,
    BR-DEC-001).

    Two distinct call sites, per the epic's "critical timing nuance":
    - `app.policies.application.compliance_review_service.trigger_review` calls this
      directly, in the SAME transaction as the review it just completed, for an aggregate
      `APPROVE` or `BLOCK` outcome -- no human approval step is needed for either
      (docs/03-domain/approvals.md: "BLOCK is not reviewable through this workflow").
      This is this codebase's first write-side (not read-only "evidence port")
      cross-context call -- see that function's own docstring for the symmetric note.
    - `approval_service.approve_request`/`reject_request` call this once an approval
      chain for a `REVIEW`-outcome review reaches a terminal state (every step approved,
      or any step rejected) -- see those functions for why a `REVIEW`-outcome review has
      no `Decision` row at all while its chain is still pending.

    `valid_until`'s exact duration is a documented `TBD` (BR-DEC-004 doesn't pin a number)
    -- `settings.decision_valid_days` (default 90 days) is a plain, defensible default,
    the same "pick a number now, document it, revisit after real data" approach used for
    `settings.approval_request_sla_hours` (BR-APR-003's own TBD).

    Does not commit -- the caller commits once at the end of its own use case.
    """
    settings = get_settings()
    now = datetime.now(UTC)
    decision = Decision(
        organization_id=organization_id,
        compliance_review_id=compliance_review_id,
        status=status,
        valid_until=now + timedelta(days=settings.decision_valid_days),
    )
    DecisionRepository(session).add(decision)
    await session.flush()

    await emit_audit_event(
        session,
        event_type="decision.created",
        actor_id=actor_id,
        organization_id=organization_id,
        payload={
            "decision_id": str(decision.id),
            "compliance_review_id": str(compliance_review_id),
            "status": decision.status,
            "valid_until": decision.valid_until.isoformat(),
            "supersedes_decision_id": None,
            "created_at": now.isoformat(),
        },
    )
    return decision


async def get_decision(
    session: AsyncSession, *, organization_id: uuid.UUID, decision_id: uuid.UUID
) -> Decision:
    decision = await DecisionRepository(session).get_by_id_and_organization(
        decision_id, organization_id
    )
    if decision is None:
        raise DecisionNotFoundError()
    return decision


async def override_decision(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    actor_id: uuid.UUID,
    decision_id: uuid.UUID,
    new_status: str,
    justification: str,
) -> Decision:
    """Unlike `create_decision_for_review` (always a sub-step of another use case's own
    transaction), this function IS the entry use case for `POST /decisions/{id}/override`
    -- it commits itself, same as `compliance_review_service.trigger_review` or
    `approval_service.approve_request` do at the end of theirs.

    DEC-002/BR-DEC-003: authorized manual override with mandatory, non-empty
    justification. Sets `overridden`/`override_justification` and changes `status` in
    place -- the one documented exception to "a Decision is never edited in place"
    (that invariant is about *re-evaluation*, domain-model.md; override is a distinct,
    explicitly-modeled mutation path, see `Decision`'s own docstring). Never touches the
    underlying `RuleEvaluation`/`ApprovalRequest` records (BR-DEC-003: "without deleting
    the original evaluation record") -- this function doesn't even import those models.
    """
    if not justification or not justification.strip():
        raise EmptyJustificationError()

    decision = await get_decision(session, organization_id=organization_id, decision_id=decision_id)
    original_status = decision.status
    now = datetime.now(UTC)

    decision.overridden = True
    decision.override_justification = justification
    decision.status = new_status
    await session.flush()

    await emit_audit_event(
        session,
        event_type="decision.overridden",
        actor_id=actor_id,
        organization_id=organization_id,
        payload={
            "decision_id": str(decision.id),
            "original_outcome": original_status,
            "new_outcome": new_status,
            "justification": justification,
            "overridden_by": str(actor_id),
            "overridden_at": now.isoformat(),
        },
    )
    await session.commit()
    await session.refresh(decision)
    return decision
