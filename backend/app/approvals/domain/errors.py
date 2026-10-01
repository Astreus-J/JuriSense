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
