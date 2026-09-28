import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CreateIntegrationRequest(BaseModel):
    provider: str = Field(min_length=1, max_length=100)
    config: dict[str, Any] = Field(default_factory=dict)


class IntegrationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    provider: str
    config: dict[str, Any]
    status: str
    created_at: datetime
    updated_at: datetime
