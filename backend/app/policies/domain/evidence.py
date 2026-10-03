"""Read-only DTOs `Policy & Compliance` hands `Evidence & Audit` across its evidence port
(docs/04-architecture/components.md rule 3). Plain frozen dataclasses of primitives and
UUIDs, never ORM instances."""

import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PolicyVersionEvidenceDTO:
    policy_version_id: uuid.UUID
    policy_id: uuid.UUID
    version_number: int


@dataclass(frozen=True)
class RuleEvaluationEvidenceDTO:
    rule_evaluation_id: uuid.UUID
    rule_id: uuid.UUID
    rule_key: str
    outcome: str
    severity: str
    approver_role: str | None
    rationale: str
    evidence_refs: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class ReviewEvidenceDTO:
    compliance_review_id: uuid.UUID
    contract_version_id: uuid.UUID
    policy_versions: tuple[PolicyVersionEvidenceDTO, ...]
    rule_evaluations: tuple[RuleEvaluationEvidenceDTO, ...]
