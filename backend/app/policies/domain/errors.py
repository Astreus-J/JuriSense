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
