class ApprovalsError(Exception):
    """Domain error for the Approvals & Decisions bounded context."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NoApprovalWorkflowConfiguredError(ApprovalsError):
    """FEATURE-6.1: raised by `approval_service.create_approval_requests_for_review` when
    no `ApprovalWorkflow` exists for the given severity tier in the caller's
    organization. Shouldn't happen for an organization created after this epic
    (`workflow_service.seed_default_workflows` seeds `medium`/`high`/`critical` at
    registration time), but can for organizations created before this epic, or for the
    undocumented `low`-severity-reaches-REVIEW edge case (docs/03-domain/approvals.md's
    routing table leaves `low` unconfigured by design)."""

    def __init__(self, trigger_condition: str) -> None:
        super().__init__(
            f"No ApprovalWorkflow is configured for severity tier '{trigger_condition}'"
        )
        self.trigger_condition = trigger_condition


class ApprovalRequestNotFoundError(ApprovalsError):
    def __init__(self) -> None:
        super().__init__("Approval request not found")


class ApprovalRequestAlreadyResolvedError(ApprovalsError):
    """BR-APR-001/domain-model.md: an `ApprovalRequest` is immutable once resolved --
    mirrors `app.policies.domain.errors.PublishedRuleImmutableError`'s role for `Rule`."""

    def __init__(self) -> None:
        super().__init__("This approval request has already been resolved")


class ApproverRoleMismatchError(ApprovalsError):
    """BR-APR-001/APR-002: only a user whose `Membership.role` in this organization
    matches the request's `approver_role` may resolve it."""

    def __init__(self) -> None:
        super().__init__("Your role does not match this approval request's required approver role")


class EmptyJustificationError(ApprovalsError):
    """Shared by `approval_service.reject_request` (mandatory justification on rejection,
    docs/03-domain/approvals.md "On rejection") and `decision_service.override_decision`
    (BR-DEC-003: "mandatory, non-empty justification string")."""

    def __init__(self) -> None:
        super().__init__("A non-empty justification is required")


class DecisionNotFoundError(ApprovalsError):
    def __init__(self) -> None:
        super().__init__("Decision not found")


class DecisionAlreadyExistsError(ApprovalsError):
    """Raised by `decision_service.create_decision_for_review` when the database refuses the
    new Decision: either `decisions.uq_decisions_one_per_compliance_review` (QA/security review,
    2026-10-01: a concurrent-write race reaching the same review twice, backstopping
    `approval_service.resolve_if_pending`) or the partial unique index
    `uq_decisions_one_active_per_contract_version` (FEATURE-6.5: a racing completion on the same
    ContractVersion already made a newer Decision effective). Either way the transaction has
    been rolled back, so no superseded predecessor is left without its successor. Handled
    cleanly as a 409, never a raw 500."""

    def __init__(self) -> None:
        super().__init__("A Decision already exists for this compliance review")


class DecisionReviewNotFoundError(ApprovalsError):
    """FEATURE-6.5: raised by `decision_service.create_decision_for_review` when the review it
    was asked to package is not in the caller's organization. Never reveals whether the id
    exists elsewhere (ADR-003)."""

    def __init__(self) -> None:
        super().__init__("Compliance review not found")


class DecisionNotEffectiveError(ApprovalsError):
    """BR-DEC-002/BR-DEC-003: only the effective (`ACTIVE`) Decision can be overridden. A
    `SUPERSEDED` Decision is historical -- overriding it would edit a record the lifecycle has
    already closed, and the override would never reach anything a caller reads as current.
    Raised by `decision_service.override_decision` when its conditional UPDATE matches no row
    (the Decision exists in the caller's organization but is no longer ACTIVE)."""

    def __init__(self) -> None:
        super().__init__("Only the effective decision for this contract version can be overridden")


class OverriddenDecisionSupersessionError(ApprovalsError):
    """FEATURE-6.5 / BR-DEC-003: an automatic re-evaluation chain must never silently replace a
    Decision a human overrode. Raised by `decision_service.create_decision_for_review` when a
    re-evaluation (an explicit `supersedes_decision_id`) would move an overridden, ACTIVE Decision
    to SUPERSEDED. Raised before any write, so the surrounding transaction rolls back. Replacing
    an override is a human action: a manual review (no supersedes link) is still allowed to
    supersede it."""

    def __init__(self) -> None:
        super().__init__(
            "This decision was manually overridden. A human must replace it with a manual review; "
            "an automatic re-evaluation cannot supersede it"
        )
