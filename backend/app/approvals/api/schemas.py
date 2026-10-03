import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ApprovalRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    compliance_review_id: uuid.UUID
    approval_workflow_id: uuid.UUID
    approver_role: str
    step_number: int
    status: str
    justification: str | None
    resolved_by: uuid.UUID | None
    resolved_at: datetime | None
    requested_at: datetime
    created_at: datetime
    updated_at: datetime


class ApproveRequestBody(BaseModel):
    """Justification is optional on approval (docs/03-domain/approvals.md)."""

    justification: str | None = Field(default=None, max_length=5000)


class RejectRequestBody(BaseModel):
    """Justification is mandatory and non-empty on rejection (BR-APR-002/approvals.md
    "On rejection") -- enforced again in `approval_service.reject_request` itself, since
    `min_length=1` alone would still accept a whitespace-only string."""

    justification: str = Field(min_length=1, max_length=5000)


class DecisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    compliance_review_id: uuid.UUID
    status: str
    # FEATURE-6.5: "ACTIVE" is the single effective Decision for its ContractVersion; "SUPERSEDED"
    # is historical. `status` remains the APPROVE|REVIEW|BLOCK outcome.
    lifecycle: str
    valid_until: datetime
    supersedes_decision_id: uuid.UUID | None
    overridden: bool
    override_justification: str | None
    created_at: datetime
    updated_at: datetime


class OverrideDecisionRequest(BaseModel):
    new_status: Literal["APPROVE", "REVIEW", "BLOCK"]
    justification: str = Field(min_length=1, max_length=5000)
