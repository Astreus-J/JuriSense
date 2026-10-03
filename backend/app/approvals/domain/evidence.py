"""Read-only DTOs `Approvals & Decisions` hands `Evidence & Audit` across its evidence port
(docs/04-architecture/components.md rule 3). Primitives and UUIDs only, never ORM instances."""

import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class DecisionFacts:
    """The fields of one Decision that its EvidencePackage records. Passed by value so the
    Evidence context never reads the `decisions` table itself."""

    organization_id: uuid.UUID
    decision_id: uuid.UUID
    compliance_review_id: uuid.UUID
    contract_version_id: uuid.UUID
    status: str
    supersedes_decision_id: uuid.UUID | None
    created_at: datetime


@dataclass(frozen=True)
class ReviewerRecord:
    """One human approval step of a review's chain: who resolved it (`resolved_by`) and in what
    role/step. `resolved_by` / `resolved_at` are None while the step is still pending."""

    approval_request_id: uuid.UUID
    approver_role: str
    step_number: int
    status: str
    resolved_by: uuid.UUID | None
    resolved_at: datetime | None
