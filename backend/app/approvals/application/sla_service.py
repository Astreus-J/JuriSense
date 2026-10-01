"""SLA expiry for pending `ApprovalRequest`s (BR-APR-003, STORY-6.2.3;
docs/03-domain/approvals.md "SLA and escalation").

BR-APR-003 explicitly marks the exact SLA duration `TBD` pending customer discovery; this
implements the epic brief's documented hackathon simplification: a flat
`settings.approval_request_sla_hours` (default 48h = 2 "business days", treated as a flat
wall-clock duration) rather than the full per-tier table `approvals.md` describes as the
longer-term candidate, and "business days" is treated as a further simplifying TBD too --
real business-day/calendar arithmetic is out of scope for this round.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.approvals.infrastructure.repositories import ApprovalRequestRepository
from app.core.config import get_settings
from app.evidence.application.audit_service import emit_audit_event


async def expire_stale_approval_requests(session: AsyncSession) -> int:
    """Transitions every `pending` `ApprovalRequest` older than the configured SLA to
    `expired` and emits an escalation `AuditEvent` for each (BR-APR-003: "exceeds its
    configured SLA... emits an escalation event"). An `expired` request never produces a
    `Decision` -- per docs/03-domain/approvals.md, it blocks the review from reaching one
    until an admin intervenes, and that admin-intervention path is explicit future work
    (not built this round) -- so this function simply leaves the review without a
    `Decision`, same as a still-pending chain.

    `approval.expired` is catalogued in docs/03-domain/audit.md's event list, following
    that catalog's existing `<context>.<action>` convention.

    QA/security review (2026-10-01): a human's `approve_request`/`reject_request` call
    landing between this function's own `list_pending_requested_before` SELECT and its
    commit used to be silently clobbered -- this loaded each row, mutated `status` in
    Python, and committed unconditionally, with no awareness that a concurrent human
    resolution might have already committed first. Each row is now transitioned via
    `ApprovalRequestRepository.expire_pending_if_pending`'s atomic conditional UPDATE
    (mirroring `resolve_if_pending`'s fix on the human side) -- if a human won the race
    for a given row, this function's own attempt simply does nothing for that row (no
    audit event, no error) rather than overwriting their resolution.

    Commits itself -- this is the Celery task's own entry point
    (`app.approvals.infrastructure.tasks.expire_stale_approval_requests_task`), run via
    `app.core.db.task_session()`, never the FastAPI request session.
    """
    settings = get_settings()
    cutoff = datetime.now(UTC) - timedelta(hours=settings.approval_request_sla_hours)
    repository = ApprovalRequestRepository(session)
    stale_requests = await repository.list_pending_requested_before(cutoff)

    expired_count = 0
    for request in stale_requests:
        won = await repository.expire_pending_if_pending(request.id)
        if not won:
            continue
        expired_count += 1
        expired_at = datetime.now(UTC)
        await emit_audit_event(
            session,
            event_type="approval.expired",
            actor_id=None,
            organization_id=request.organization_id,
            payload={
                "approval_request_id": str(request.id),
                "compliance_review_id": str(request.compliance_review_id),
                "approver_role": request.approver_role,
                "step_number": request.step_number,
                "requested_at": request.requested_at.isoformat(),
                "expired_at": expired_at.isoformat(),
            },
        )

    await session.commit()
    return expired_count
