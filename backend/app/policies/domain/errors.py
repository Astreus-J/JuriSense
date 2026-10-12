class PolicyError(Exception):
    """Domain error for the Policy & Compliance bounded context."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class PolicyNotFoundError(PolicyError):
    def __init__(self) -> None:
        super().__init__("Policy not found")


class PolicyVersionNotFoundError(PolicyError):
    def __init__(self) -> None:
        super().__init__("Policy version not found")


class RuleNotFoundError(PolicyError):
    def __init__(self) -> None:
        super().__init__("Rule not found")


class RuleValidationError(PolicyError):
    """The rule YAML/grammar is malformed, references an unknown context field, or its
    `when` clause does not compile to a valid CEL expression (#55/#57) -- raised before
    anything is saved to a draft, never after (`policy-engine.md`: "a syntactically
    invalid rule is rejected... never silently accepted")."""


class DuplicateRuleKeyError(PolicyError):
    """A `rule.id` (business key, e.g. "LGPD-001") must be unique within one
    PolicyVersion -- domain-model.md's "Rule" identity."""

    def __init__(self, rule_key: str) -> None:
        super().__init__(f"A rule with id '{rule_key}' already exists in this policy version")
        self.rule_key = rule_key


class PolicyVersionNotDraftError(PolicyError):
    """BR-POL-001: a Rule is created/edited only inside a draft PolicyVersion; a
    published PolicyVersion's rules are frozen permanently."""

    def __init__(self) -> None:
        super().__init__("Rules can only be created or edited inside a draft policy version")


class PublishedRuleImmutableError(PolicyError):
    """BR-POL-001, enforced at the domain (ORM) layer, not just the service/API layer --
    see `Rule`'s `@validates` guard in `app.policies.infrastructure.models`."""

    def __init__(self) -> None:
        super().__init__("A rule belonging to a published policy version cannot be modified")


class NoDraftVersionToPublishError(PolicyError):
    def __init__(self) -> None:
        super().__init__("Only a draft policy version can be published")


class ContractVersionNotFoundError(PolicyError):
    """Phase 5 (#123): raised when a `ComplianceReview` is triggered against a
    `contract_version_id` that doesn't exist, or whose `Contract` isn't in the caller's
    organization -- distinct from "exists but extraction hasn't produced evidence yet",
    which is a valid state to trigger a review in (BR-CMP-001: `contract.*` rules simply
    come back `NOT_APPLICABLE`), see
    `app.contracts.application.evidence_service.contract_version_belongs_to_organization`."""

    def __init__(self) -> None:
        super().__init__("Contract version not found")


class ComplianceReviewNotFoundError(PolicyError):
    def __init__(self) -> None:
        super().__init__("Compliance review not found")


class PolicyVersionConflictError(PolicyError):
    """QA review (2026-09-30): two concurrent requests can race on either of two unique
    constraints -- two concurrent publishes of different draft versions of the same
    Policy both targeting `uq_policy_versions_one_current`, or two concurrent "create
    draft version" calls computing the same "next" version_number and colliding on
    `uq_policy_version_number`. Both previously surfaced as an unhandled 500
    (uncaught IntegrityError) instead of a clean 409, the same bug class already found
    and fixed for ContractVersion re-uploads. The client should simply retry."""

    def __init__(self) -> None:
        super().__init__(
            "Another request just changed this policy's versions -- retry the operation"
        )


class PolicyLimitExceededError(PolicyError):
    """#180 (security finding POL-004): a per-organization resource-exhaustion backstop,
    checked in `policy_service.create_policy` before a new `Policy` row is created --
    unbounded Policies is an unbounded `Rule`-evaluation cost lever (every currently-
    published Policy's Rules get pooled into every `trigger_review`/`simulate` call,
    `compliance_review_service`'s own "multi-policy pooling" design decision)."""

    def __init__(self, limit: int) -> None:
        super().__init__(
            f"This organization has reached its limit of {limit} policies"
        )


class PolicyVersionLimitExceededError(PolicyError):
    """#180: same resource-exhaustion backstop as `PolicyLimitExceededError`, scoped per
    Policy instead of per organization -- checked in `policy_service.create_draft_version`."""

    def __init__(self, limit: int) -> None:
        super().__init__(
            f"This policy has reached its limit of {limit} versions"
        )


class RuleLimitExceededError(PolicyError):
    """#180: same resource-exhaustion backstop, scoped per PolicyVersion -- checked in
    `rule_service.create_rule`. The real cost driver `trigger_review`/`simulate` pay per
    call is the total pooled Rule count across every currently-published PolicyVersion, so
    this is the most directly load-bearing of the three #180 caps."""

    def __init__(self, limit: int) -> None:
        super().__init__(
            f"This policy version has reached its limit of {limit} rules"
        )


class ExceptionJustificationRequiredError(PolicyError):
    """#120 (STORY-4.4.2): mirrors the empty-justification guard used for the evidence
    override flow (`EvidenceOverrideJustificationRequiredError`) -- a `PolicyException`
    with no stated reason defeats the entire point of an auditable, time-boxed waiver."""

    def __init__(self) -> None:
        super().__init__("A justification is required to grant a policy exception")


class ExceptionTargetInvalidError(PolicyError):
    """#120: a `PolicyException` targets exactly one of `supplier_id`/`contract_version_id`
    -- never both, never neither. The scope is one or the other because the two evidence
    ports that validate target ownership (`get_supplier_identity`/
    `contract_version_belongs_to_organization`) are mutually exclusive lookups; there is
    no existing concept of a combined supplier+contract target anywhere else in this
    domain to reuse."""

    def __init__(self) -> None:
        super().__init__(
            "A policy exception must target exactly one of supplier_id or contract_version_id"
        )


class ExceptionTargetNotFoundError(PolicyError):
    """#120: the given `supplier_id`/`contract_version_id` does not exist, or is not in
    the caller's organization -- same indistinguishable-404 discipline as
    `ContractVersionNotFoundError`."""

    def __init__(self) -> None:
        super().__init__("Exception target not found")


class RuleNotEligibleForExceptionError(PolicyError):
    """#120: only a `REVIEW`-tier rule (one with a non-null `approver_role`) can be
    waived. A `BLOCK`-tier rule structurally has no `approver_role`
    (`rule_dsl.parse_rule_yaml`'s own validation) -- there is no single role whose
    sign-off could stand in for a BLOCK finding, so exceptions are out of scope for
    BLOCK-tier rules until a separate decision says otherwise."""

    def __init__(self) -> None:
        super().__init__(
            "Only a REVIEW-tier rule (one with an approver_role) is eligible for an exception"
        )


class ActorNotAuthorizedForExceptionError(PolicyError):
    """#120: granting an exception requires the actor to themselves hold an ACTIVE
    `Membership` whose `role` equals the waived rule's own `approver_role` -- the same
    role that would otherwise have to sign off on this exact rule's REVIEW, mirroring
    `approval_service`'s own role-match-or-reject pattern for approving a real
    `ApprovalRequest`."""

    def __init__(self) -> None:
        super().__init__(
            "Only a user holding this rule's approver role may grant an exception for it"
        )


class ExceptionValidUntilMustBeFutureError(PolicyError):
    """#120: a time-boxed exception that is already expired at creation time is not a
    waiver, it's a no-op that would mislead an auditor reading the grant event."""

    def __init__(self) -> None:
        super().__init__("A policy exception's valid_until must be in the future")


class ActiveExceptionLimitExceededError(PolicyError):
    """Security review (2026-10-12), same POL-004 resource-exhaustion backstop as
    `RuleLimitExceededError` et al., scoped per Rule: nothing else bounds how many active
    `PolicyException` rows one Rule can accumulate, and `list_active_for_rule_ids` scans
    all of them on every `trigger_review`/`simulate` call."""

    def __init__(self, limit: int) -> None:
        super().__init__(f"This rule has reached its limit of {limit} active exceptions")
