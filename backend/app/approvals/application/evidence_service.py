"""`ApprovalsEvidencePort` (docs/04-architecture/components.md rule 3): the sanctioned way
`Evidence & Audit` reads Approvals data. Plain application-layer functions returning DTOs,
never ORM instances or repositories."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.approvals.domain.evidence import DecisionFacts, ReviewerRecord
from app.approvals.infrastructure.models import Decision
from app.approvals.infrastructure.repositories import ApprovalRequestRepository


async def list_reviewers_for_review(
    session: AsyncSession, *, organization_id: uuid.UUID, compliance_review_id: uuid.UUID
) -> list[ReviewerRecord]:
    """Every ApprovalRequest step of one review, in step order, scoped to the caller's
    organization. Empty for an APPROVE or BLOCK review, which has no approval chain."""
    requests = await ApprovalRequestRepository(session).list_by_review(
        compliance_review_id, organization_id
    )
    return [
        ReviewerRecord(
            approval_request_id=request.id,
            approver_role=request.approver_role,
            step_number=request.step_number,
            status=request.status,
            resolved_by=request.resolved_by,
            resolved_at=request.resolved_at,
        )
        for request in requests
    ]


async def list_all_decision_facts(session: AsyncSession) -> list[DecisionFacts]:
    """Every Decision on the platform, across organizations. Used ONLY by the one-off backfill
    that creates packages for Decisions that predate EVD-001 (`evidence_package_service.
    backfill_missing_packages`); no user-facing path may call this."""
    result = await session.execute(select(Decision).order_by(Decision.created_at, Decision.id))
    return [
        DecisionFacts(
            organization_id=decision.organization_id,
            decision_id=decision.id,
            compliance_review_id=decision.compliance_review_id,
            contract_version_id=decision.contract_version_id,
            status=decision.status,
            supersedes_decision_id=decision.supersedes_decision_id,
            created_at=decision.created_at,
        )
        for decision in result.scalars()
    ]
