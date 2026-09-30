"""Unit tests for `app.policies.domain.rule_dsl` -- the YAML DSL parser/validator/CEL
compiler (#55/#57). Includes the 5 worked examples from
docs/03-domain/policy-engine.md verbatim, and the missing-field/NOT_APPLICABLE behavior
the ADR-004 spike validated (see rule_dsl.py's module docstring)."""

import celpy
import pytest

from app.policies.domain.errors import RuleValidationError
from app.policies.domain.rule_dsl import parse_rule_yaml

LGPD_001 = """
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

LEGAL_008 = """
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

FIN_003 = """
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

FIN_004 = """
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

SANC_001 = """
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


def _eval(expr: str, context: dict) -> bool:
    env = celpy.Environment()
    program = env.program(env.compile(expr))
    return bool(program.evaluate(celpy.json_to_cel(context)))


@pytest.mark.parametrize(
    ("yaml_text", "rule_key", "expected_status", "expected_severity", "expected_approver"),
    [
        (LGPD_001, "LGPD-001", "BLOCK", "critical", None),
        (LEGAL_008, "LEGAL-008", "REVIEW", "high", "legal"),
        (FIN_003, "FIN-003", "REVIEW", "medium", "legal"),
        (FIN_004, "FIN-004", "REVIEW", "high", "director"),
        (SANC_001, "SANC-001", "BLOCK", "critical", None),
    ],
)
def test_parses_worked_examples_from_policy_engine_doc(
    yaml_text, rule_key, expected_status, expected_severity, expected_approver
) -> None:
    parsed = parse_rule_yaml(yaml_text)
    assert parsed.rule_key == rule_key
    assert parsed.result_status == expected_status
    assert parsed.severity == expected_severity
    assert parsed.approver_role == expected_approver
    # Compiled CEL must itself be valid (parse_rule_yaml already verifies this, but
    # re-verify independently here so this test doesn't just trust the implementation).
    celpy.Environment().compile(parsed.compiled_presence_cel)
    celpy.Environment().compile(parsed.compiled_condition_cel)


def test_lgpd_001_matches_when_processing_without_dpa() -> None:
    parsed = parse_rule_yaml(LGPD_001)
    ctx = {"contract": {"processes_personal_data": True, "dpa_present": False}}
    assert _eval(parsed.compiled_presence_cel, ctx) is True
    assert _eval(parsed.compiled_condition_cel, ctx) is True


def test_lgpd_001_does_not_match_when_dpa_present() -> None:
    parsed = parse_rule_yaml(LGPD_001)
    ctx = {"contract": {"processes_personal_data": True, "dpa_present": True}}
    assert _eval(parsed.compiled_presence_cel, ctx) is True
    assert _eval(parsed.compiled_condition_cel, ctx) is False


def test_fin_003_and_fin_004_threshold_boundaries() -> None:
    fin_003 = parse_rule_yaml(FIN_003)
    fin_004 = parse_rule_yaml(FIN_004)
    ctx = {"contract": {"value": {"brl": 300000}}}
    assert _eval(fin_003.compiled_condition_cel, ctx) is True
    assert _eval(fin_004.compiled_condition_cel, ctx) is False


# --- Missing-field / NOT_APPLICABLE semantics (the ADR-004 spike's core finding) ---


def test_presence_check_is_false_when_referenced_field_entirely_absent() -> None:
    """A genuinely absent key -- has() correctly returns False, no CELEvalError."""
    parsed = parse_rule_yaml(FIN_003)
    assert _eval(parsed.compiled_presence_cel, {"contract": {"value": {}}}) is False
    assert _eval(parsed.compiled_presence_cel, {"contract": {}}) is False
    assert _eval(parsed.compiled_presence_cel, {}) is False


def test_condition_would_error_on_a_present_but_null_leaf() -> None:
    """The documented reason the context builder must OMIT an inapplicable field rather
    than setting it to `null`: has() alone does not protect a present-but-null leaf, so
    evaluating the condition directly against a null value raises -- callers must never
    do this; `context_builder.normalize_context` is what prevents it from ever happening
    in practice."""
    parsed = parse_rule_yaml(FIN_003)
    ctx = {"contract": {"value": {"brl": None}}}
    assert _eval(parsed.compiled_presence_cel, ctx) is True  # has() sees the key as present
    with pytest.raises(celpy.evaluation.CELEvalError):
        _eval(parsed.compiled_condition_cel, ctx)


# --- Unknown-field / syntax rejection (#57) ---


def test_rejects_unknown_field_reference() -> None:
    bad = """
rule:
  id: BAD-001
  name: Bad rule
when:
  contract.not_a_real_field: true
result:
  status: BLOCK
severity: critical
approver_role: null
"""
    with pytest.raises(RuleValidationError, match="not a recognized evaluation-context field"):
        parse_rule_yaml(bad)


def test_rejects_invalid_yaml_syntax() -> None:
    with pytest.raises(RuleValidationError, match="Invalid YAML"):
        parse_rule_yaml("rule: [unterminated")


def test_rejects_missing_rule_id() -> None:
    bad = """
rule:
  name: Missing id
when:
  supplier.sanctions_hit: true
result:
  status: BLOCK
severity: critical
approver_role: null
"""
    with pytest.raises(RuleValidationError, match="rule.id"):
        parse_rule_yaml(bad)


def test_rejects_review_without_approver_role() -> None:
    bad = """
rule:
  id: BAD-002
  name: Review without approver
when:
  supplier.sanctions_hit: true
result:
  status: REVIEW
severity: high
approver_role: null
"""
    with pytest.raises(RuleValidationError, match="approver_role"):
        parse_rule_yaml(bad)


def test_rejects_block_with_approver_role() -> None:
    bad = """
rule:
  id: BAD-003
  name: Block with approver
when:
  supplier.sanctions_hit: true
result:
  status: BLOCK
severity: critical
approver_role: legal
"""
    with pytest.raises(RuleValidationError, match="approver_role"):
        parse_rule_yaml(bad)


def test_rejects_invalid_severity() -> None:
    bad = """
rule:
  id: BAD-004
  name: Bad severity
when:
  supplier.sanctions_hit: true
result:
  status: BLOCK
severity: catastrophic
approver_role: null
"""
    with pytest.raises(RuleValidationError, match="severity"):
        parse_rule_yaml(bad)


def test_rejects_ambiguous_operator_mapping() -> None:
    bad = """
rule:
  id: BAD-005
  name: Ambiguous operator
when:
  contract.value.brl: { gte: 1000, lte: 2000 }
result:
  status: REVIEW
severity: low
approver_role: finance
"""
    with pytest.raises(RuleValidationError, match="exactly one operator key"):
        parse_rule_yaml(bad)


def test_in_ne_lt_operators_compile_and_evaluate_correctly() -> None:
    """Rounds out coverage of every operator `_OPERATORS` supports, not just the `gte`
    the doc's worked examples happen to use."""
    in_rule = parse_rule_yaml(
        """
rule:
  id: OP-IN
  name: In operator
when:
  contract.jurisdiction: { in: ["BR", "PT"] }
result:
  status: REVIEW
severity: low
approver_role: legal
"""
    )
    assert _eval(in_rule.compiled_condition_cel, {"contract": {"jurisdiction": "BR"}}) is True
    assert _eval(in_rule.compiled_condition_cel, {"contract": {"jurisdiction": "US"}}) is False

    ne_rule = parse_rule_yaml(
        """
rule:
  id: OP-NE
  name: Ne operator
when:
  contract.liability.type: { ne: unlimited }
result:
  status: REVIEW
severity: low
approver_role: legal
"""
    )
    assert (
        _eval(ne_rule.compiled_condition_cel, {"contract": {"liability": {"type": "capped"}}})
        is True
    )
    assert (
        _eval(ne_rule.compiled_condition_cel, {"contract": {"liability": {"type": "unlimited"}}})
        is False
    )

    lt_rule = parse_rule_yaml(
        """
rule:
  id: OP-LT
  name: Lt operator
when:
  contract.value.brl: { lt: 1000 }
result:
  status: REVIEW
severity: low
approver_role: legal
"""
    )
    assert _eval(lt_rule.compiled_condition_cel, {"contract": {"value": {"brl": 500}}}) is True
    assert _eval(lt_rule.compiled_condition_cel, {"contract": {"value": {"brl": 5000}}}) is False


def test_rejects_unknown_operator() -> None:
    bad = """
rule:
  id: BAD-006
  name: Unknown operator
when:
  contract.value.brl: { between: [1, 2] }
result:
  status: REVIEW
severity: low
approver_role: finance
"""
    with pytest.raises(RuleValidationError, match="Unknown comparison operator"):
        parse_rule_yaml(bad)
