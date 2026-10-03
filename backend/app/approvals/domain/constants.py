"""Approvals & Decisions vocabulary -- see docs/03-domain/domain-model.md
("ApprovalWorkflow", "ApprovalRequest", "Decision") and docs/03-domain/approvals.md (the
full behavioral spec this vocabulary implements)."""

from enum import StrEnum


class ApprovalRequestStatus(StrEnum):
    """`ApprovalRequest`'s state machine (docs/03-domain/approvals.md "ApprovalRequest
    state machine"): pending -> approved|rejected|expired, all three terminal and
    immutable once reached (see `app.approvals.infrastructure.models.ApprovalRequest`'s
    `@validates` guard)."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class DecisionStatus(StrEnum):
    """The final, packaged compliance outcome for a `ComplianceReview`
    (docs/03-domain/domain-model.md "Decision"). Deliberately the same three values as
    `app.policies.domain.constants.ComplianceReviewStatus`'s terminal outcomes -- `Decision`
    has no "pending" value (domain-model.md), so a review stuck mid-approval-chain simply
    has no `Decision` row yet, rather than one in some intermediate state."""

    APPROVE = "APPROVE"
    REVIEW = "REVIEW"
    BLOCK = "BLOCK"


class SeverityTier(StrEnum):
    """The `ApprovalWorkflow.trigger_condition` vocabulary -- a plain severity-tier
    string, intentionally **not** an import of `app.policies.domain.constants.Severity`
    (see `tests/approvals/test_boundary_rules.py`): Policy & Compliance already depends on
    Approvals & Decisions (`trigger_review` calls into this context), so Approvals
    importing Policies' domain types back would create a cross-context cycle. This local
    enum's *values* are the same four tier names by convention, not by shared code --
    `app.policies.application.compliance_review_service` passes the tier as a plain `str`
    (see that module's own docstring for the "primitives only" cross-context-call rule).
    """

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ReviewRequiredReason(StrEnum):
    """`decisions.review_required_reason` vocabulary (BR-DEC-004, FEATURE-6.4) -- the
    `reason` payload of `compliance.review_required` (docs/03-domain/audit.md). Precedence
    when several apply at once: expired, then contract_changed, then policy_changed (see
    `app.approvals.application.reevaluation_service`). `supplier_changed` is catalogued in
    audit.md but deliberately not implemented yet (supplier-profile triggers are a
    follow-up, not part of this story's acceptance criteria)."""

    EXPIRED = "expired"
    CONTRACT_CHANGED = "contract_changed"
    POLICY_CHANGED = "policy_changed"
