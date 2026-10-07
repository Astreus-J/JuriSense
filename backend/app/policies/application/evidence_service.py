"""`PolicyEvidencePort` (docs/04-architecture/components.md rule 3): the one sanctioned way
`Evidence & Audit` reads a ComplianceReview's inputs and results -- a plain application-layer
function returning DTOs, never a cross-context ORM import. Mirrors
`app.contracts.application.evidence_service`.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.policies.domain.evidence import (
    PolicyVersionEvidenceDTO,
    ReviewEvidenceDTO,
    RuleEvaluationEvidenceDTO,
)
from app.policies.infrastructure.repositories import (
    ComplianceReviewRepository,
    PolicyVersionRepository,
    RuleEvaluationRepository,
)


async def get_review_evidence(
    session: AsyncSession, *, organization_id: uuid.UUID, compliance_review_id: uuid.UUID
) -> ReviewEvidenceDTO | None:
    """Returns `None` if the review does not exist in the caller's organization. Otherwise
    returns every PolicyVersion the review pooled (with its version_number) and every
    RuleEvaluation it produced."""
    review = await ComplianceReviewRepository(session).get_by_id_and_organization(
        compliance_review_id, organization_id
    )
    if review is None:
        return None

    pooled_ids = [uuid.UUID(raw) for raw in review.policy_version_ids]
    versions = await PolicyVersionRepository(session).list_by_ids_and_organization(
        pooled_ids, organization_id
    )
    evaluations = await RuleEvaluationRepository(session).list_by_review(review.id)

    return ReviewEvidenceDTO(
        compliance_review_id=review.id,
        contract_version_id=review.contract_version_id,
        policy_versions=tuple(
            PolicyVersionEvidenceDTO(
                policy_version_id=version.id,
                policy_id=version.policy_id,
                version_number=version.version_number,
            )
            for version in versions
        ),
        rule_evaluations=tuple(
            RuleEvaluationEvidenceDTO(
                rule_evaluation_id=evaluation.id,
                rule_id=evaluation.rule_id,
                rule_key=evaluation.rule_key,
                rule_name=evaluation.rule_name,
                outcome=evaluation.outcome,
                severity=evaluation.severity,
                approver_role=evaluation.approver_role,
                rationale=evaluation.rationale,
                evidence_refs=list(evaluation.evidence_refs or []),
            )
            for evaluation in evaluations
        ),
    )
