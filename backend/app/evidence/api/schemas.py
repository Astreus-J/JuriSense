import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class EvidenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: str
    ref_id: str
    payload: dict[str, Any]
    content_hash: str


class EvidenceOverrideAddendumResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    evidence_package_id: uuid.UUID
    decision_id: uuid.UUID
    sequence_number: int
    original_status: str
    new_status: str
    justification: str
    overridden_by: uuid.UUID
    overridden_at: datetime
    previous_hash: str | None
    content_hash: str


class EvidencePackageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    decision_id: uuid.UUID
    merkle_root: str
    evidence_count: int
    created_at: datetime
    evidence: list[EvidenceResponse]
    override_addenda: list[EvidenceOverrideAddendumResponse]


class RecomputeResponse(BaseModel):
    evidence_package_id: uuid.UUID
    stored_merkle_root: str
    recomputed_merkle_root: str
    matches: bool
    evidence_count: int
    mismatched_evidence_ids: list[uuid.UUID]


class PassportDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    document_id: uuid.UUID
    content_hash: str
    mime_type: str
    size_bytes: int


class PassportAiExecutionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    provider: str | None
    model_name: str | None
    prompt_version: str | None
    extracted_at: str | None


class PassportPolicyVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    policy_version_id: uuid.UUID
    policy_id: uuid.UUID
    version_number: int


class PassportRuleEvaluationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rule_evaluation_id: uuid.UUID
    rule_id: uuid.UUID
    rule_key: str
    rule_name: str
    outcome: str
    severity: str
    approver_role: str | None
    rationale: str


class PassportReviewerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    approval_request_id: uuid.UUID
    approver_role: str
    step_number: int
    status: str
    resolved_by: uuid.UUID | None
    resolved_at: datetime | None


class DecisionPassportResponse(BaseModel):
    """FEATURE-7.3 / STORY-7.3.1: the "why was this approved?" read-model, assembled fresh
    on every read from already-immutable records (docs/03-domain/evidence.md) -- nothing
    here is itself persisted."""

    model_config = ConfigDict(from_attributes=True)

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
    documents: list[PassportDocumentResponse]
    ai_execution: PassportAiExecutionResponse | None
    policy_versions: list[PassportPolicyVersionResponse]
    rule_evaluations: list[PassportRuleEvaluationResponse]
    external_sources_consulted: list[str]
    reviewers: list[PassportReviewerResponse]
    evidence_package_id: uuid.UUID
    merkle_root: str
    evidence_count: int


class BlockchainAnchorResponse(BaseModel):
    """FEATURE-8.2. `provider == "transparency_log"` must be rendered as a labeled fallback
    by every caller, never presented as a blockchain anchor (docs/09-planning/risks.md risk 4)
    -- this response carries the raw value verbatim; the labeling is a display-layer concern."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    evidence_package_id: uuid.UUID
    provider: str
    anchor_ref: str
    status: str
    proof: dict[str, Any] | None
    submitted_at: datetime
    confirmed_at: datetime | None


class PublicVerificationResponse(BaseModel):
    """FEATURE-8.3: the ENTIRE public surface of the verification page
    (docs/06-blockchain/verification.md) -- deliberately just these five fields, never a
    supplier/contract/organization identifier. See `verification_service`'s own module
    docstring for the privacy boundary this shape enforces."""

    model_config = ConfigDict(from_attributes=True)

    status: str
    evidence_hash: str | None
    provider: str | None
    confirmed_at: str | None
    reference_url: str | None
