"""Policy & Compliance vocabulary -- see docs/03-domain/domain-model.md ("Policy",
"PolicyVersion", "Rule") and docs/03-domain/policy-engine.md (the rule DSL and
evaluation-context semantics this vocabulary implements)."""

from enum import StrEnum


class PolicyStatus(StrEnum):
    """Container-level lifecycle per domain-model.md: draft -> published -> (new version
    published) -> archived. A Policy becomes `published` the moment its first
    PolicyVersion is published; it stays `published` across subsequent republishes.
    `archived` is a future/manual action -- no transition into it exists yet in this
    epic's scope (EPIC-4 stories #57/#58/#60/#61 never call for it)."""

    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class PolicyVersionStatus(StrEnum):
    """A PolicyVersion is `draft` (its Rules are mutable, created/edited freely) until
    published, at which point it becomes `published` and every Rule it owns is frozen
    (BR-POL-001) permanently -- there is no transition back to draft."""

    DRAFT = "draft"
    PUBLISHED = "published"


class RuleResultStatus(StrEnum):
    """The *authored* status a Rule's `result.status` carries in the DSL
    (docs/03-domain/policy-engine.md) -- what happens when the rule's `when` condition
    matches. Distinct from `RuleOutcome` below, which is the *computed* per-evaluation
    result (a rule authored as BLOCK produces the RuleOutcome BLOCK when it matches, PASS
    when it doesn't, and NOT_APPLICABLE when required context is missing)."""

    APPROVE = "APPROVE"
    REVIEW = "REVIEW"
    BLOCK = "BLOCK"


class RuleOutcome(StrEnum):
    """Per-rule evaluation outcome (ADR-010 / docs/03-domain/domain-model.md
    "RuleEvaluation"). Phase 5 (EPIC-5) persists these into real `RuleEvaluation` rows;
    this epic's rule-execution engine (#61) produces values of this shape without
    persisting them."""

    PASS = "PASS"
    REVIEW = "REVIEW"
    BLOCK = "BLOCK"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class Severity(StrEnum):
    """docs/03-domain/policy-engine.md "Severity & escalation" -- drives required-approver
    tie-breaking among REVIEW rules, never the APPROVE/REVIEW/BLOCK aggregation itself."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# ADR-010 §2 / policy-engine.md "Rule priority & conflicting rules": when multiple REVIEW
# rules trigger, the required approver is the highest-severity rule's role. Index 0 is
# highest.
SEVERITY_ORDER: tuple[Severity, ...] = (
    Severity.CRITICAL,
    Severity.HIGH,
    Severity.MEDIUM,
    Severity.LOW,
)
