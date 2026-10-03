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


class EvidencePackageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    decision_id: uuid.UUID
    merkle_root: str
    evidence_count: int
    created_at: datetime
    evidence: list[EvidenceResponse]


class RecomputeResponse(BaseModel):
    evidence_package_id: uuid.UUID
    stored_merkle_root: str
    recomputed_merkle_root: str
    matches: bool
    evidence_count: int
    mismatched_evidence_ids: list[uuid.UUID]
