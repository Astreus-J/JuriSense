import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.integrations.domain.credential_fields import transform_sensitive_values

MASKED_VALUE = "********"


def _mask_sensitive(value: Any) -> Any:
    """Security review (H1, 2026-10-03): connector credentials were returned in plaintext to
    AUDITOR and SECURITY. Responses now keep the shape of `config` but replace the value of any
    credential-like key, at any depth, with a fixed mask. Storage is handled separately (at-rest
    encryption, `infrastructure/credential_encryption.py`) -- this mask applies the same whether
    the underlying stored value is plaintext or an encrypted token, since it never looks at the
    value itself, only the key."""
    return transform_sensitive_values(value, lambda _: MASKED_VALUE)


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

    @field_validator("config", mode="after")
    @classmethod
    def _mask_credentials(cls, config: dict[str, Any]) -> dict[str, Any]:
        return _mask_sensitive(config)
