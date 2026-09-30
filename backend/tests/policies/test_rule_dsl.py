"""Unit tests for `app.policies.domain.rule_dsl` -- the YAML DSL parser/validator/CEL
compiler (#55/#57). Includes the 5 worked examples from
docs/03-domain/policy-engine.md verbatim, and the missing-field/NOT_APPLICABLE behavior
the ADR-004 spike validated (see rule_dsl.py's module docstring)."""

from typing import Any

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


def test_numeric_comparison_does_not_crash_on_int_double_type_mismatch() -> None:
    """QA finding (2026-09-30): a rule's `when` numeric literal and the runtime
    evaluation-context value for the same field can be cel-python IntType/DoubleType
    respectively (or vice versa) -- cel-python does not consider them comparable and
    raises an uncaught `CELEvalError: no such overload` instead of the intended
    True/False, which previously propagated as an unhandled 500 through
    `evaluate_policy_version` -> `trigger_review`/`run_simulation`. Both directions are
    covered: FIN_003's `when` literal (`gte: 250000`, an int) against a float context
    value, and a rule whose own literal is a float against an int context value."""
    fin_003 = parse_rule_yaml(FIN_003)  # when: { gte: 250000 } -- an int literal
    float_ctx = {"contract": {"value": {"brl": 300000.0}}}  # a double context value
    assert _eval(fin_003.compiled_condition_cel, float_ctx) is True

    decimal_threshold = """
rule:
  id: FIN-005
  name: Decimal Threshold Regression
when:
  contract.value.brl: { gte: 250000.0 }
result:
  status: REVIEW
severity: medium
approver_role: legal
"""
    parsed = parse_rule_yaml(decimal_threshold)  # when: { gte: 250000.0 } -- a float literal
    int_ctx = {"contract": {"value": {"brl": 300000}}}  # an int context value
    assert _eval(parsed.compiled_condition_cel, int_ctx) is True


# --- Missing-field / NOT_APPLICABLE semantics (the ADR-004 spike's core finding) ---


def test_presence_check_is_false_when_referenced_field_entirely_absent() -> None:
    """A genuinely absent key -- has() correctly returns False, no CELEvalError."""
    parsed = parse_rule_yaml(FIN_003)
    assert _eval(parsed.compiled_presence_cel, {"contract": {"value": {}}}) is False
    assert _eval(parsed.compiled_presence_cel, {"contract": {}}) is False
    assert _eval(parsed.compiled_presence_cel, {}) is False


def test_condition_is_false_not_error_on_a_present_but_null_numeric_leaf() -> None:
    """The documented reason the context builder must OMIT an inapplicable field rather
    than setting it to `null`: has() alone does not protect a present-but-null leaf. For a
    numeric comparison, CEL's `double(...)` cast (added to symmetrically resolve
    IntType/DoubleType overload mismatches -- see `rule_dsl._numeric_cel_literal`) also
    happens to accept `null` without raising, evaluating the comparison to `False` instead
    of the `CELEvalError` a raw (uncast) comparison would raise. This is a silent-failure
    mode, not a crash, if the context builder's null-leaf-omission invariant is ever
    violated -- `context_builder.normalize_context` is what actually prevents a null leaf
    from reaching here in production, and remains the real safety net regardless of this
    behavior."""
    parsed = parse_rule_yaml(FIN_003)
    ctx = {"contract": {"value": {"brl": None}}}
    assert _eval(parsed.compiled_presence_cel, ctx) is True  # has() sees the key as present
    assert _eval(parsed.compiled_condition_cel, ctx) is False


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


def test_resolve_path_rejects_ambiguous_bare_field_name(monkeypatch: pytest.MonkeyPatch) -> None:
    """`resolve_path`'s bare-suffix fallback (module docstring point 4) must reject a bare
    name that matches more than one registered context path rather than silently picking
    one -- no such collision exists in the real `ALL_CONTEXT_PATHS` today (every bare
    suffix is currently unique), so the ambiguous branch is exercised here by patching in
    two paths that share a suffix, the way a future context-schema addition could."""
    import app.policies.domain.rule_dsl as rule_dsl_module

    monkeypatch.setattr(
        rule_dsl_module,
        "ALL_CONTEXT_PATHS",
        frozenset({"contract.risk_score", "supplier.risk_score"}),
    )
    with pytest.raises(RuleValidationError, match="ambiguous"):
        rule_dsl_module.resolve_path("risk_score")


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


def test_rejects_pathologically_deeply_nested_when_literal_via_yaml() -> None:
    """QA finding POL-003 (2026-09-30): a `when` clause with a deeply nested list literal
    (an author submitting raw YAML text, e.g. thousands of `[`s) previously blew PyYAML's
    own recursive-descent parser with an uncaught `RecursionError` -- a rule create/update
    must always fail as a clean `RuleValidationError`, never a 500, regardless of how
    pathological the input is."""
    depth = 3000
    nested_literal = "[" * depth + "1" + "]" * depth
    bad = f"""
rule:
  id: POL-003-TEST
  name: Recursion Test
when:
  contract.value.brl: {{ in: {nested_literal} }}
result:
  status: REVIEW
severity: medium
approver_role: legal
"""
    with pytest.raises(RuleValidationError, match="too deeply nested"):
        parse_rule_yaml(bad)


def test_rejects_pathologically_deeply_nested_when_literal_via_direct_dict() -> None:
    """Same POL-003 finding, but via `parse_rule_document`'s direct-dict entry point (the
    one a future no-code rule builder would use, per its own docstring) -- the recursion
    there happens inside `compile_rule_when`/`_cel_literal`/CEL's own compiler, not
    PyYAML, so it needs its own guard."""
    from app.policies.domain.rule_dsl import parse_rule_document

    nested: Any = 1
    for _ in range(3000):
        nested = [nested]
    doc = {
        "rule": {"id": "POL-003-TEST", "name": "Recursion Test"},
        "when": {"contract.value.brl": {"in": nested}},
        "result": {"status": "REVIEW"},
        "severity": "medium",
        "approver_role": "legal",
    }
    with pytest.raises(RuleValidationError, match="too deeply nested"):
        parse_rule_document(doc)


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
