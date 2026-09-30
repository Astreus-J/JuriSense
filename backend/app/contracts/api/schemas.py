import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ContractResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    supplier_id: uuid.UUID
    title: str
    contract_type: str
    status: str
    created_at: datetime
    updated_at: datetime


class ContractVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    contract_id: uuid.UUID
    document_id: uuid.UUID
    version_number: int
    status: str
    extracted_data: dict[str, Any]
    extraction_confidence: float | None
    extraction_failure_reason: str | None
    created_at: datetime
    # Not an ORM column -- populated by the route from `low_confidence_paths()` (see
    # app.contracts.domain.extracted_data) using the same dotted-path format
    # ConfirmContractVersionRequest.corrections expects as keys. Frontend detail/
    # confirmation screens need this to know *which* fields to render a correction input
    # for; without it they'd have to duplicate the threshold-walking logic client-side
    # and would need Settings.contract_extraction_confidence_threshold exposed via API,
    # which nothing else currently does.
    needs_confirmation_paths: list[str] = Field(default_factory=list)


class ClauseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    contract_version_id: uuid.UUID
    clause_type: str
    page: int
    text_span: dict[str, int]
    confidence: float
    text_excerpt: str | None


class ConfirmContractVersionRequest(BaseModel):
    """CON-005: `corrections` maps a dotted field path (see
    `app.contracts.domain.extracted_data.iter_field_leaves`) to a human-corrected value.
    Omit a path (or send `corrections: {}`/omit the body) to confirm every low-confidence
    field as-is."""

    corrections: dict[str, Any] = Field(default_factory=dict)
