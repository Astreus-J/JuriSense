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
