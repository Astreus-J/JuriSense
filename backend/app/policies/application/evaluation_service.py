"""The rule-execution engine (#61): evaluates one `PolicyVersion`'s `Rule`s (draft or
published) against one normalized evaluation context (#60) and returns each rule's
outcome with rationale -- the actual CEL evaluation the ADR-004 spike (#55) validated,
now wired to real `Rule` rows and real evidence.

This module has no knowledge of `ComplianceReview`/`RuleEvaluation` (Phase 5/EPIC-5
tables that don't exist yet) -- it returns plain `RuleEvaluationResult` objects shaped to
be trivially convertible into a future `RuleEvaluation` row, per this epic's brief
("your rule-execution engine's per-rule output shape must be compatible with what Phase 5
will consume"), without creating one itself.
"""

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import celpy

from app.policies.domain.constants import SEVERITY_ORDER, RuleOutcome, Severity
from app.policies.domain.rule_dsl import describe_when
from app.policies.infrastructure.models import Rule

_CEL_ENV = celpy.Environment()


@lru_cache(maxsize=2048)
def _compiled_program(expression: str) -> celpy.Runner:
    """Compiling a CEL expression (`env.compile` + `env.program`) measured ~1.6ms per
    rule-evaluation when done fresh on every call -- well over the "well under a
    millisecond" target from the #55 spike. Evaluating an already-compiled program,
    by contrast, measured ~0.06ms (see ADR-004's spike findings). Since a `Rule`'s
    `compiled_presence_cel`/`compiled_condition_cel` strings are immutable once written
    (BR-POL-001 for a published rule; unchanged for the lifetime of a single simulation
    run even for a draft rule), caching the compiled program by expression string is
    always safe -- the cache key is the exact CEL source text, not the rule identity, so
    two different rules that happen to compile to the same expression also correctly
    share one cache entry."""
    return _CEL_ENV.program(_CEL_ENV.compile(expression))


@dataclass(frozen=True)
class RuleEvaluationResult:
    """One rule's evaluation result -- the per-rule shape `ADR-010`'s future
    `RuleEvaluation` persists; `rule_id`/`rule_key`/`rule_name` together let a caller
    render this without a second lookup, `rationale` is the human-readable "why" the
    product's "WHY, EVIDENCE, POLICY, SOURCE" principle (ADR-010) requires."""

    rule_id: str
    rule_key: str
    rule_name: str
    outcome: str
    severity: str
    approver_role: str | None
    rationale: str


@dataclass(frozen=True)
class AggregatePreview:
    """The ADR-010 §2 order-independent aggregation, computed here purely as a
    *simulation preview* (#61) -- never persisted as a real `ComplianceReview`/`Decision`."""

    status: str
    required_approver_roles: tuple[str, ...]


def _cel_eval(expression: str, context: dict[str, Any]) -> bool:
    program = _compiled_program(expression)
    result = program.evaluate(celpy.json_to_cel(context))
    return bool(result)


def evaluate_rule(rule: Rule, context: dict[str, Any]) -> RuleEvaluationResult:
    """Two-phase evaluation (see `app.policies.domain.rule_dsl`'s module docstring for
    why): first confirm every referenced context field is present (`compiled_presence_cel`)
    -- if not, the outcome is `NOT_APPLICABLE`, distinct from a genuinely non-matching
    condition. Only once presence is confirmed is `compiled_condition_cel` evaluated."""
    present = _cel_eval(rule.compiled_presence_cel, context)
    if not present:
        return RuleEvaluationResult(
            rule_id=str(rule.id),
            rule_key=rule.rule_key,
            rule_name=rule.name,
            outcome=RuleOutcome.NOT_APPLICABLE.value,
            severity=rule.severity,
            approver_role=None,
            rationale=(
                f"Rule '{rule.rule_key}' is not applicable -- one or more required "
                "evaluation-context fields are missing from the available supplier/"
                "contract evidence."
            ),
        )

    matched = _cel_eval(rule.compiled_condition_cel, context)
    if matched:
        return RuleEvaluationResult(
            rule_id=str(rule.id),
            rule_key=rule.rule_key,
            rule_name=rule.name,
            outcome=rule.result_status,
            severity=rule.severity,
            approver_role=rule.approver_role,
            rationale=f"Rule '{rule.rule_key}' condition matched: {describe_when(rule.when)}.",
        )

    return RuleEvaluationResult(
        rule_id=str(rule.id),
        rule_key=rule.rule_key,
        rule_name=rule.name,
        outcome=RuleOutcome.PASS.value,
        severity=rule.severity,
        approver_role=None,
        rationale=f"Rule '{rule.rule_key}' condition did not match -- no violation found.",
    )


def evaluate_policy_version(
    rules: list[Rule], context: dict[str, Any]
) -> list[RuleEvaluationResult]:
    """Every rule in `rules` is evaluated independently, order-independent per ADR-010 --
    the list is returned in the same order `rules` was given, but nothing about the
    result depends on that order."""
    return [evaluate_rule(rule, context) for rule in rules]


def aggregate_preview(results: list[RuleEvaluationResult]) -> AggregatePreview:
    """ADR-010 §2: any BLOCK -> BLOCK; else any REVIEW -> REVIEW (required approver(s) =
    the highest-severity triggered REVIEW rule's role(s), ties broken by naming every
    distinct role at that severity -- "escalate rather than under-notify"); else APPROVE.
    """
    if any(r.outcome == RuleOutcome.BLOCK.value for r in results):
        return AggregatePreview(status=RuleOutcome.BLOCK.value, required_approver_roles=())

    review_results = [r for r in results if r.outcome == RuleOutcome.REVIEW.value]
    if not review_results:
        return AggregatePreview(status="APPROVE", required_approver_roles=())

    severities_present = {Severity(r.severity) for r in review_results}
    highest = next(s for s in SEVERITY_ORDER if s in severities_present)
    roles = sorted(
        {r.approver_role for r in review_results if r.severity == highest.value and r.approver_role}
    )
    return AggregatePreview(status=RuleOutcome.REVIEW.value, required_approver_roles=tuple(roles))
