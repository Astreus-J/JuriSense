"""FEATURE-7.3 / STORY-7.3.1: the Decision Passport -- "a complete, reproducible 'why was
this approved?' narrative for any Decision" (docs/03-domain/evidence.md).

## Design: the same facts, read twice, for two different purposes
`evidence_package_service._build_leaves` turns these same underlying facts into `Evidence`
leaves -- hashes and commitments, so the result is cryptographically verifiable
(`BR-EVD-001`). This module reads the identical facts through the identical evidence ports,
but keeps them in their plain, human-readable form, because a narrative that only shows
hashes answers "was this altered?" and not "why was this approved?" -- the two questions
this context exists to answer together. Nothing here is persisted: this is a pure read-model
assembled fresh from already-immutable rows on every call.

## Design: 404s collapse the same way the raw EvidencePackage endpoint's already do
A missing Decision, one in another organization, and one with no package yet are all
indistinguishable to the caller (ADR-003) -- mirrors `evidence_package_service.
get_package_for_decision`'s own contract, which this module calls first for exactly that
reason.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.approvals.application.evidence_service import (
    get_decision_summary,
    list_reviewers_for_review,
)
from app.approvals.domain.evidence import ReviewerRecord
from app.contracts.application.evidence_service import get_contract_version_evidence
from app.evidence.application.evidence_package_service import get_package_for_decision
from app.evidence.domain.errors import EvidenceError, EvidencePackageNotFoundError
from app.policies.application.evidence_service import get_review_evidence
from app.policies.domain.evidence import ReviewEvidenceDTO
from app.suppliers.application.evidence_service import (
    get_supplier_check_evidence,
    get_supplier_identity,
)

# Mirrors `evidence_package_service._SUPPLIER_PROFILE_SOURCE`: the one `evidence_refs`
# `source` value that points at a SupplierCheck. Kept as its own constant here rather than
# imported, the same way that module is self-contained rather than reaching into Policy's
# evidence-ref shape from outside -- both read the same wire contract independently.
_SUPPLIER_PROFILE_SOURCE = "supplier_profile"


@dataclass(frozen=True)
class PassportDocument:
    document_id: uuid.UUID
    content_hash: str
    mime_type: str
    size_bytes: int


@dataclass(frozen=True)
class PassportAiExecution:
    provider: str | None
    model_name: str | None
    prompt_version: str | None
    extracted_at: str | None


@dataclass(frozen=True)
class PassportPolicyVersion:
    policy_version_id: uuid.UUID
    policy_id: uuid.UUID
    version_number: int


@dataclass(frozen=True)
class PassportRuleEvaluation:
    rule_evaluation_id: uuid.UUID
    rule_id: uuid.UUID
    rule_key: str
    rule_name: str
    outcome: str
    severity: str
    approver_role: str | None
    rationale: str


@dataclass(frozen=True)
class PassportReviewer:
    approval_request_id: uuid.UUID
    approver_role: str
    step_number: int
    status: str
    resolved_by: uuid.UUID | None
    resolved_at: datetime | None


@dataclass(frozen=True)
class DecisionPassport:
    decision_id: uuid.UUID
    status: str
    lifecycle: str
    valid_until: datetime
    overridden: bool
    override_justification: str | None
    supersedes_decision_id: uuid.UUID | None
    created_at: datetime
    compliance_review_id: uuid.UUID
    supplier_id: uuid.UUID
    supplier_legal_name: str
    supplier_tax_id: str
    contract_id: uuid.UUID
    contract_title: str
    contract_version_id: uuid.UUID
    contract_version_number: int
    documents: tuple[PassportDocument, ...]
    ai_execution: PassportAiExecution | None
    policy_versions: tuple[PassportPolicyVersion, ...]
    rule_evaluations: tuple[PassportRuleEvaluation, ...]
    external_sources_consulted: tuple[str, ...]
    reviewers: tuple[PassportReviewer, ...]
    evidence_package_id: uuid.UUID
    merkle_root: str
    evidence_count: int


async def get_decision_passport(
    session: AsyncSession, *, organization_id: uuid.UUID, decision_id: uuid.UUID
) -> DecisionPassport:
    package_view = await get_package_for_decision(
        session, organization_id=organization_id, decision_id=decision_id
    )
    summary = await get_decision_summary(
        session, organization_id=organization_id, decision_id=decision_id
    )
    if summary is None:
        # Should be unreachable: a package's `decision_id` FK guarantees the Decision row
        # exists. Defensive backstop, not a reachable path -- mirrors
        # `DecisionAlreadyExistsError`'s own "should be effectively unreachable" framing.
        raise EvidencePackageNotFoundError()

    review = await get_review_evidence(
        session,
        organization_id=organization_id,
        compliance_review_id=summary.compliance_review_id,
    )
    if review is None:
        raise EvidenceError("Cannot build Decision Passport: compliance review not found")
    contract = await get_contract_version_evidence(
        session, organization_id=organization_id, contract_version_id=summary.contract_version_id
    )
    if contract is None:
        raise EvidenceError("Cannot build Decision Passport: contract version not found")
    supplier = await get_supplier_identity(
        session, organization_id=organization_id, supplier_id=contract.supplier_id
    )
    if supplier is None:
        raise EvidenceError("Cannot build Decision Passport: supplier not found")

    reviewers = await list_reviewers_for_review(
        session,
        organization_id=organization_id,
        compliance_review_id=summary.compliance_review_id,
    )
    sources = await _external_sources_consulted(
        session, organization_id=organization_id, review=review
    )

    ai_execution = (
        PassportAiExecution(
            provider=contract.extraction_provider,
            model_name=contract.extraction_model_name,
            prompt_version=contract.extraction_prompt_version,
            extracted_at=contract.extracted_at,
        )
        if contract.extraction_run_id is not None
        else None
    )

    return DecisionPassport(
        decision_id=summary.decision_id,
        status=summary.status,
        lifecycle=summary.lifecycle,
        valid_until=summary.valid_until,
        overridden=summary.overridden,
        override_justification=summary.override_justification,
        supersedes_decision_id=summary.supersedes_decision_id,
        created_at=summary.created_at,
        compliance_review_id=summary.compliance_review_id,
        supplier_id=supplier.supplier_id,
        supplier_legal_name=supplier.legal_name,
        supplier_tax_id=supplier.tax_id,
        contract_id=contract.contract_id,
        contract_title=contract.contract_title,
        contract_version_id=contract.contract_version_id,
        contract_version_number=contract.version_number,
        documents=(
            PassportDocument(
                document_id=contract.document_id,
                content_hash=contract.document_content_hash,
                mime_type=contract.document_mime_type,
                size_bytes=contract.document_size_bytes,
            ),
        ),
        ai_execution=ai_execution,
        policy_versions=tuple(
            PassportPolicyVersion(
                policy_version_id=version.policy_version_id,
                policy_id=version.policy_id,
                version_number=version.version_number,
            )
            for version in review.policy_versions
        ),
        rule_evaluations=tuple(
            PassportRuleEvaluation(
                rule_evaluation_id=evaluation.rule_evaluation_id,
                rule_id=evaluation.rule_id,
                rule_key=evaluation.rule_key,
                rule_name=evaluation.rule_name,
                outcome=evaluation.outcome,
                severity=evaluation.severity,
                approver_role=evaluation.approver_role,
                rationale=evaluation.rationale,
            )
            for evaluation in review.rule_evaluations
        ),
        external_sources_consulted=sources,
        reviewers=tuple(_passport_reviewer(record) for record in reviewers),
        evidence_package_id=package_view.package.id,
        merkle_root=package_view.package.merkle_root,
        evidence_count=package_view.package.evidence_count,
    )


def _passport_reviewer(record: ReviewerRecord) -> PassportReviewer:
    return PassportReviewer(
        approval_request_id=record.approval_request_id,
        approver_role=record.approver_role,
        step_number=record.step_number,
        status=record.status,
        resolved_by=record.resolved_by,
        resolved_at=record.resolved_at,
    )


async def _external_sources_consulted(
    session: AsyncSession, *, organization_id: uuid.UUID, review: ReviewEvidenceDTO
) -> tuple[str, ...]:
    """Every distinct external source any SupplierCheck the review's rule evaluations
    referenced consulted (e.g. the CNPJ registry, CEIS/CNEP/CEPIM), deduplicated and sorted
    for a stable narrative. A review with no supplier-sourced rule evaluation returns an
    empty tuple -- that is a legitimate "no supplier evidence was used" case, not an error.

    QA review (2026-10-06): a check that WAS referenced but doesn't resolve is a different
    case entirely -- this Passport only exists because the Decision's EvidencePackage was
    already assembled, which means every one of these same check ids resolved at that time
    (`evidence_package_service._supplier_check_leaves` raises on exactly this condition
    during assembly). A `None` here now means something has gone missing since, which is
    corruption, not a benign empty case -- mirrors that sibling function's choice to raise
    rather than silently produce an incomplete narrative."""
    check_ids = {
        ref.get("supplier_check_id")
        for evaluation in review.rule_evaluations
        for ref in evaluation.evidence_refs
        if ref.get("source") == _SUPPLIER_PROFILE_SOURCE
        and ref.get("supplier_check_id") is not None
    }
    sources: set[str] = set()
    for check_id in check_ids:
        check = await get_supplier_check_evidence(
            session, organization_id=organization_id, supplier_check_id=uuid.UUID(check_id)
        )
        if check is None:
            raise EvidenceError("Cannot build Decision Passport: supplier check not found")
        sources.update(check.sources_consulted)
    return tuple(sorted(sources))
