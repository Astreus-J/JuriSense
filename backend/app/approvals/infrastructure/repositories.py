import uuid
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.approvals.domain.constants import ApprovalRequestStatus
from app.approvals.infrastructure.models import ApprovalRequest, ApprovalWorkflow, Decision


class ApprovalWorkflowRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, workflow: ApprovalWorkflow) -> None:
        self._session.add(workflow)

    async def get_by_organization_and_trigger(
        self, organization_id: uuid.UUID, trigger_condition: str
    ) -> ApprovalWorkflow | None:
        result = await self._session.execute(
            select(ApprovalWorkflow).where(
                ApprovalWorkflow.organization_id == organization_id,
                ApprovalWorkflow.trigger_condition == trigger_condition,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, workflow_id: uuid.UUID) -> ApprovalWorkflow | None:
        return await self._session.get(ApprovalWorkflow, workflow_id)

    async def list_by_organization(self, organization_id: uuid.UUID) -> list[ApprovalWorkflow]:
        result = await self._session.execute(
            select(ApprovalWorkflow).where(ApprovalWorkflow.organization_id == organization_id)
        )
        return list(result.scalars())


class ApprovalRequestRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, request: ApprovalRequest) -> None:
        self._session.add(request)

    async def get_by_id_and_organization(
        self, request_id: uuid.UUID, organization_id: uuid.UUID
    ) -> ApprovalRequest | None:
        result = await self._session.execute(
            select(ApprovalRequest).where(
                ApprovalRequest.id == request_id,
                ApprovalRequest.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_review(
        self, compliance_review_id: uuid.UUID, organization_id: uuid.UUID
    ) -> list[ApprovalRequest]:
        result = await self._session.execute(
            select(ApprovalRequest)
            .where(
                ApprovalRequest.compliance_review_id == compliance_review_id,
                ApprovalRequest.organization_id == organization_id,
            )
            .order_by(ApprovalRequest.step_number)
        )
        return list(result.scalars())

    async def list_pending_requested_before(self, cutoff: datetime) -> list[ApprovalRequest]:
        """BR-APR-003 SLA expiry: every `pending` request whose `requested_at` is older
        than `cutoff` -- across every organization, since the Celery task
        (`app.approvals.infrastructure.tasks.expire_stale_approval_requests_task`) runs
        platform-wide, not per-tenant. Used only to discover *candidates* for the audit
        event payload (id/organization_id/approver_role/etc.) -- the actual transition is
        `expire_pending_if_pending` below, never a plain attribute mutation on the objects
        this returns (see that method's docstring for why)."""
        result = await self._session.execute(
            select(ApprovalRequest).where(
                ApprovalRequest.status == ApprovalRequestStatus.PENDING.value,
                ApprovalRequest.requested_at < cutoff,
            )
        )
        return list(result.scalars())

    async def resolve_if_pending(
        self,
        request_id: uuid.UUID,
        *,
        status: str,
        justification: str | None,
        resolved_by: uuid.UUID,
        resolved_at: datetime,
    ) -> bool:
        """QA/security review (2026-10-01): `approve_request`/`reject_request` previously
        loaded the row, checked `status == PENDING` in Python, then mutated ORM attributes
        and flushed -- a classic read-then-write race. Two callers (two users who both
        hold the required `approver_role`, or one approving while another rejects the same
        step) could both pass the Python check before either committed, both proceed to
        instantiate a next step or create a `Decision`, and silently produce duplicate/
        contradictory rows with no error surfaced to either caller (both get 200).

        This is a single atomic `UPDATE ... WHERE id = :id AND status = 'pending'`,
        executed via SQLAlchemy Core (bypassing `ApprovalRequest._guard_resolved`'s
        `@validates` hooks entirely, since a Core-level bulk update never touches ORM
        instance attributes) -- the database's own row-level locking during the UPDATE is
        what actually serializes two concurrent resolution attempts now, not a
        Python-level check. Returns `True` if this call won the race (exactly one caller
        ever does, for any given request); `False` means another transaction already
        resolved it -- the caller must treat that as `ApprovalRequestAlreadyResolvedError`,
        exactly as if the earlier Python-level check had caught it.

        Callers must `session.refresh()` the ORM object afterward if they continue using
        it -- this bypasses the identity map's normal attribute-tracking, so the in-memory
        object is stale (still shows `status="pending"`) until refreshed."""
        result = await self._session.execute(
            update(ApprovalRequest)
            .where(
                ApprovalRequest.id == request_id,
                ApprovalRequest.status == ApprovalRequestStatus.PENDING.value,
            )
            .values(
                status=status,
                justification=justification,
                resolved_by=resolved_by,
                resolved_at=resolved_at,
            )
        )
        return result.rowcount > 0

    async def expire_pending_if_pending(self, request_id: uuid.UUID) -> bool:
        """The SLA-sweep side of the same race `resolve_if_pending` closes from the human
        side (QA/security review, 2026-10-01): the Celery task's own transition must be an
        equally atomic conditional `UPDATE`, or a human's `approve`/`reject` landing
        between this task's `SELECT` (`list_pending_requested_before`) and its old
        load-then-mutate `commit()` could have its result silently clobbered back to
        `expired` with no error on either side. Returns `True` only if THIS call
        transitioned the row (still `pending` at UPDATE time) -- `False` means a human (or
        a different worker run) already resolved it first, and the caller should skip
        emitting an `approval.expired` audit event for it. `ApprovalRequest` has no
        `expired_at` column of its own (only `resolved_at`, for a human resolution) -- the
        audit event's own `expired_at` payload field is a point-in-time value the caller
        generates, not something this method persists on the row."""
        result = await self._session.execute(
            update(ApprovalRequest)
            .where(
                ApprovalRequest.id == request_id,
                ApprovalRequest.status == ApprovalRequestStatus.PENDING.value,
            )
            .values(status=ApprovalRequestStatus.EXPIRED.value)
        )
        return result.rowcount > 0


class DecisionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, decision: Decision) -> None:
        self._session.add(decision)

    async def get_by_id_and_organization(
        self, decision_id: uuid.UUID, organization_id: uuid.UUID
    ) -> Decision | None:
        result = await self._session.execute(
            select(Decision).where(
                Decision.id == decision_id, Decision.organization_id == organization_id
            )
        )
        return result.scalar_one_or_none()

    async def get_by_review(
        self, compliance_review_id: uuid.UUID, organization_id: uuid.UUID
    ) -> Decision | None:
        result = await self._session.execute(
            select(Decision).where(
                Decision.compliance_review_id == compliance_review_id,
                Decision.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()
