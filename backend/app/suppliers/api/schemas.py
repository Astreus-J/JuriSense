import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.suppliers.domain.constants import SupplierStatus


class CreateSupplierRequest(BaseModel):
    legal_name: str = Field(min_length=1, max_length=255)
    tax_id: str = Field(min_length=1, max_length=32)
    jurisdiction: str = Field(default="BR", min_length=2, max_length=2)


class UpdateSupplierStatusRequest(BaseModel):
    status: SupplierStatus


class SupplierResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    legal_name: str
    tax_id: str
    jurisdiction: str
    status: str
    created_at: datetime
    updated_at: datetime


class SupplierCheckResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    supplier_id: uuid.UUID
    status: str
    sources_consulted: list[str]
    raw_results: dict[str, Any]
    failure_reason: str | None
    started_at: datetime
    completed_at: datetime | None
