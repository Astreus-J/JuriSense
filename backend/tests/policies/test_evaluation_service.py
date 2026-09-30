"""#61: the rule-execution engine -- per-rule PASS/REVIEW/BLOCK/NOT_APPLICABLE outcomes
and the ADR-010 aggregation preview. Uses the same 5 worked examples as
tests/policies/test_rule_dsl.py, now run through `evaluate_rule`/`evaluate_policy_version`
against a real `Rule` ORM instance (constructed directly, no database needed -- these are
pure-Python evaluations)."""

import uuid

from app.policies.application.evaluation_service import (
    aggregate_preview,
    evaluate_policy_version,
    evaluate_rule,
)
from app.policies.domain.constants import RuleOutcome
from app.policies.domain.rule_dsl import parse_rule_yaml
from app.policies.infrastructure.models import Rule


def _rule_from_yaml(yaml_text: str) -> Rule:
    parsed = parse_rule_yaml(yaml_text)
    return Rule(
        id=uuid.uuid4(),
        policy_version_id=uuid.uuid4(),
        rule_key=parsed.rule_key,
        name=parsed.name,
        when=parsed.when,
        result_status=parsed.result_status,
        severity=parsed.severity,
        approver_role=parsed.approver_role,
        compiled_presence_cel=parsed.compiled_presence_cel,
        compiled_condition_cel=parsed.compiled_condition_cel,
    )


LGPD_001_YAML = """
rule:
  id: LGPD-001
  name: DPA Required for Personal Data Processing
when:
  processes_personal_data: true
  dpa_present: false
result:
  status: BLOCK
severity: critical
approver_role: null
"""

SANC_001_YAML = """
rule:
  id: SANC-001
  name: Supplier on a Sanctions List
when:
  supplier.sanctions_hit: true
result:
  status: BLOCK
severity: critical
approver_role: null
"""

FIN_003_YAML = """
rule:
  id: FIN-003
  name: High-Value Contract Requires Legal Approval
when:
  contract.value.brl: { gte: 250000 }
result:
  status: REVIEW
severity: medium
approver_role: legal
"""

FIN_004_YAML = """
rule:
  id: FIN-004
  name: Very High-Value Contract Requires Legal + Director Approval
when:
  contract.value.brl: { gte: 1000000 }
result:
  status: REVIEW
severity: high
approver_role: director
"""

LEGAL_008_YAML = """
rule:
  id: LEGAL-008
  name: Unlimited Liability Requires Legal Review
when:
  contract.liability.type: unlimited
result:
  status: REVIEW
severity: high
approver_role: legal
"""


def test_evaluate_rule_blocks_on_match() -> None:
    rule = _rule_from_yaml(LGPD_001_YAML)
    context = {"contract": {"processes_personal_data": True, "dpa_present": False}}
    result = evaluate_rule(rule, context)
    assert result.outcome == RuleOutcome.BLOCK.value
    assert result.rule_key == "LGPD-001"
    assert result.approver_role is None


def test_evaluate_rule_passes_when_condition_not_met() -> None:
    rule = _rule_from_yaml(LGPD_001_YAML)
    context = {"contract": {"processes_personal_data": True, "dpa_present": True}}
    result = evaluate_rule(rule, context)
    assert result.outcome == RuleOutcome.PASS.value


def test_evaluate_rule_not_applicable_when_field_missing() -> None:
    """The core NOT_APPLICABLE-vs-PASS distinction the ADR-004 spike's two-phase design
    exists for: an empty context (no supplier evidence available at all) must never be
    silently treated as "sanctions_hit is falsy"."""
    rule = _rule_from_yaml(SANC_001_YAML)
    result = evaluate_rule(rule, {})
    assert result.outcome == RuleOutcome.NOT_APPLICABLE.value
    assert "not applicable" in result.rationale.lower()


def test_evaluate_rule_blocks_when_sanctions_hit_present() -> None:
    rule = _rule_from_yaml(SANC_001_YAML)
    result = evaluate_rule(rule, {"supplier": {"sanctions_hit": True}})
    assert result.outcome == RuleOutcome.BLOCK.value


def test_evaluate_rule_rationale_is_human_readable_not_a_python_repr() -> None:
    """QA review (2026-09-30): `rationale` previously rendered `repr(rule.when)` verbatim
    (e.g. `{'contract.value.brl': {'gte': 250000}}`) -- raw Python dict syntax, not the
    human-readable condition text ADR-010's "WHY, EVIDENCE, POLICY, SOURCE" explainability
    principle calls for. `describe_when` must render the DSL's own operator symbols
    instead of Python's dict/repr syntax."""
    rule = _rule_from_yaml(FIN_003_YAML)
    result = evaluate_rule(rule, {"contract": {"value": {"brl": 300000}}})
    assert result.outcome == "REVIEW"
    assert "{'gte':" not in result.rationale
    assert "contract.value.brl >= 250000" in result.rationale


def test_evaluate_policy_version_runs_every_rule_independently() -> None:
    rules = [_rule_from_yaml(SANC_001_YAML), _rule_from_yaml(FIN_003_YAML)]
    context = {"supplier": {"sanctions_hit": False}, "contract": {"value": {"brl": 300000}}}
    results = evaluate_policy_version(rules, context)
    assert len(results) == 2
    by_key = {r.rule_key: r for r in results}
    assert by_key["SANC-001"].outcome == RuleOutcome.PASS.value
    assert by_key["FIN-003"].outcome == RuleOutcome.REVIEW.value


def test_aggregate_preview_any_block_wins() -> None:
    rules = [_rule_from_yaml(SANC_001_YAML), _rule_from_yaml(FIN_003_YAML)]
    context = {"supplier": {"sanctions_hit": True}, "contract": {"value": {"brl": 300000}}}
    results = evaluate_policy_version(rules, context)
    aggregate = aggregate_preview(results)
    assert aggregate.status == RuleOutcome.BLOCK.value
    assert aggregate.required_approver_roles == ()


def test_aggregate_preview_review_requires_highest_severity_approver() -> None:
    """FIN-003 (medium/legal) and FIN-004 (high/director) both trigger on a >=1,000,000
    BRL contract; ADR-010 says the required approver is the *highest-severity* triggered
    rule's role -- here that's FIN-004's `director`, not FIN-003's `legal`."""
    rules = [_rule_from_yaml(FIN_003_YAML), _rule_from_yaml(FIN_004_YAML)]
    context = {"contract": {"value": {"brl": 1500000}}}
    results = evaluate_policy_version(rules, context)
    aggregate = aggregate_preview(results)
    assert aggregate.status == RuleOutcome.REVIEW.value
    assert aggregate.required_approver_roles == ("director",)


def test_aggregate_preview_ties_name_every_distinct_role_at_highest_severity() -> None:
    rules = [_rule_from_yaml(LEGAL_008_YAML), _rule_from_yaml(FIN_004_YAML)]
    context = {
        "contract": {
            "liability": {"type": "unlimited"},
            "value": {"brl": 1500000},
        }
    }
    results = evaluate_policy_version(rules, context)
    aggregate = aggregate_preview(results)
    assert aggregate.status == RuleOutcome.REVIEW.value
    # Both LEGAL-008 and FIN-004 are severity=high -- tie, so both roles are named.
    assert aggregate.required_approver_roles == ("director", "legal")


def test_aggregate_preview_approve_when_everything_passes_or_not_applicable() -> None:
    rules = [_rule_from_yaml(SANC_001_YAML), _rule_from_yaml(FIN_003_YAML)]
    results = evaluate_policy_version(rules, {})
    aggregate = aggregate_preview(results)
    assert all(r.outcome == RuleOutcome.NOT_APPLICABLE.value for r in results)
    assert aggregate.status == "APPROVE"
    assert aggregate.required_approver_roles == ()
