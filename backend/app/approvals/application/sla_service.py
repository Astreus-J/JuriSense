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

from app.approvals.domain.constants import ApprovalRequestStatus
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

    `approval.expired` is not yet catalogued in docs/03-domain/audit.md's event list
    (only `approval.requested`/`approval.approved`/`approval.rejected` are) -- named here
    following that catalog's existing `<context>.<action>` convention; adding it to the
    catalog is tracked as a documentation follow-up, not a behavioral gap.

    Commits itself -- this is the Celery task's own entry point
    (`app.approvals.infrastructure.tasks.expire_stale_approval_requests_task`), run via
    `app.core.db.task_session()`, never the FastAPI request session.
    """
    settings = get_settings()
    cutoff = datetime.now(UTC) - timedelta(hours=settings.approval_request_sla_hours)
    stale_requests = await ApprovalRequestRepository(session).list_pending_requested_before(cutoff)

    for request in stale_requests:
        request.status = ApprovalRequestStatus.EXPIRED.value
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
                "expired_at": datetime.now(UTC).isoformat(),
            },
        )

    await session.commit()
    return len(stale_requests)
