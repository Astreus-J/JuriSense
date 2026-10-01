import uuid
from datetime import datetime

from sqlalchemy import select
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
        platform-wide, not per-tenant."""
        result = await self._session.execute(
            select(ApprovalRequest).where(
                ApprovalRequest.status == ApprovalRequestStatus.PENDING.value,
                ApprovalRequest.requested_at < cutoff,
            )
        )
        return list(result.scalars())


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
