import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Key fragments that mark a config value as a credential. Matching is by substring on the
# lowercased key, so over-masking (e.g. "monkey") is the accepted trade-off.
_SENSITIVE_KEY_FRAGMENTS = ("secret", "token", "password", "passwd", "key", "credential", "auth")
MASKED_VALUE = "********"


def _mask_sensitive(value: Any) -> Any:
    """Security review (H1, 2026-10-03): connector credentials were returned in plaintext to
    AUDITOR and SECURITY. Responses now keep the shape of `config` but replace the value of any
    credential-like key, at any depth, with a fixed mask. Storage is not changed here."""
    if isinstance(value, dict):
        return {
            key: MASKED_VALUE
            if any(fragment in str(key).lower() for fragment in _SENSITIVE_KEY_FRAGMENTS)
            else _mask_sensitive(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_mask_sensitive(item) for item in value]
    return value


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
