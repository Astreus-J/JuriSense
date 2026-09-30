"""The Rule YAML DSL: parser, grammar validator, and CEL compiler (#55, #57;
docs/03-domain/policy-engine.md "Rule DSL"; ADR-004).

## ADR-004 spike findings this module encodes

1. **CEL errors by default on undefined field access** (`CELEvalError`), confirmed live
   against `cel-python==0.5.0`. The `has()` macro correctly guards a genuinely *absent*
   key (returns `False`, no error) but does **not** guard a key that is present with an
   explicit JSON `null` value -- `has()` only tests structural presence, so
   `has(contract.value.brl)` is `True` even when `contract.value.brl` is `null`, and the
   subsequent comparison then raises `CELEvalError` anyway. The fix is at the *context*
   side, not the CEL side: `app.policies.application.context_builder.normalize_context`
   never emits an explicit `null` leaf -- an inapplicable field is omitted from the
   context dict entirely (see `context_schema.py`'s docstring).
2. **A single has()-guarded boolean expression cannot distinguish "condition false" from
   "field missing"** -- both short-circuit `has(...) && ...` to `False`. Since
   `RuleOutcome` needs `NOT_APPLICABLE` to be distinguishable from `PASS`
   (`docs/03-domain/domain-model.md` "RuleEvaluation"), this module compiles **two**
   separate CEL expressions per rule: `presence_cel` (an AND-chain of `has()` calls, one
   per referenced path prefix) and `condition_cel` (the actual comparison, safe to
   evaluate only once presence is confirmed). `evaluation_service.evaluate_rule` runs
   them in that order.
3. **Authors never see raw CEL.** The YAML `when:` grammar (a flat mapping of
   `dotted.path -> literal-or-{op: value}`) is the only surface exposed; this module is
   solely responsible for hiding CEL's syntax from a policy author, per ADR-004's
   "Consequences".
4. **Unknown-field strictness**: every `when` key must resolve to a path in
   `context_schema.ALL_CONTEXT_PATHS` -- either directly, or (matching
   `policy-engine.md`'s own LGPD-001 example, which references `processes_personal_data`
   /`dpa_present` unprefixed even though the evaluation context exposes them as
   `contract.processes_personal_data`/`contract.dpa_present`) as an unambiguous bare
   suffix of exactly one registered path. A `when` key matching zero or more-than-one
   registered path is rejected -- this is the "unknown field reference... rejected before
   it's saved" behavior #57 calls for.
"""

import json
from dataclasses import dataclass
from typing import Any

import celpy
import yaml

from app.policies.domain.constants import RuleResultStatus, Severity
from app.policies.domain.context_schema import ALL_CONTEXT_PATHS
from app.policies.domain.errors import RuleValidationError

_CEL_ENV = celpy.Environment()

# {op_key: cel_operator}. "in" is special-cased in _compile_condition_clause below
# (CEL's `in` puts the operand on the left: `x in [1, 2, 3]`, not `[1, 2, 3] in x`).
_OPERATORS: dict[str, str] = {
    "eq": "==",
    "ne": "!=",
    "gt": ">",
    "gte": ">=",
    "lt": "<",
    "lte": "<=",
    "in": "in",
}


@dataclass(frozen=True)
class CompiledWhen:
    presence_cel: str
    condition_cel: str
    referenced_paths: tuple[str, ...]


@dataclass(frozen=True)
class ParsedRule:
    """The fully validated, compiled result of parsing one rule document -- exactly what
    `app.policies.application.rule_service.create_rule`/`update_rule` persist onto a
    `Rule` row."""

    rule_key: str
    name: str
    when: dict[str, Any]
    result_status: str
    severity: str
    approver_role: str | None
    compiled_presence_cel: str
    compiled_condition_cel: str
    referenced_paths: list[str]


def resolve_path(raw_key: str) -> str:
    """Validates one `when` key against `context_schema.ALL_CONTEXT_PATHS`, returning the
    canonical fully-qualified path. See module docstring point 4 for the bare-name
    fallback this implements."""
    if raw_key in ALL_CONTEXT_PATHS:
        return raw_key
    if "." not in raw_key:
        candidates = sorted(p for p in ALL_CONTEXT_PATHS if p.rsplit(".", 1)[-1] == raw_key)
        if len(candidates) == 1:
            return candidates[0]
        if len(candidates) > 1:
            raise RuleValidationError(
                f"'{raw_key}' is ambiguous -- it matches multiple evaluation-context "
                f"fields ({', '.join(candidates)}); use the fully-qualified path"
            )
    raise RuleValidationError(
        f"'{raw_key}' is not a recognized evaluation-context field. See "
        "docs/03-domain/policy-engine.md for the supported field list."
    )


def _cel_literal(value: Any) -> str:
    """Renders a Python value (already validated as a plain YAML/JSON scalar or list of
    scalars) as a CEL literal."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return repr(value)
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, list):
        return "[" + ", ".join(_cel_literal(item) for item in value) + "]"
    raise RuleValidationError(
        f"Unsupported value type in 'when' clause: {type(value).__name__!r}"
    )


def _compile_condition_clause(path: str, raw_key: str, raw_value: Any) -> str:
    if isinstance(raw_value, dict):
        if len(raw_value) != 1:
            raise RuleValidationError(
                f"The comparison operator for '{raw_key}' must have exactly one "
                f"operator key (e.g. {{gte: 250000}}), got {list(raw_value)}"
            )
        (op_key, op_value), = raw_value.items()
        if op_key not in _OPERATORS:
            raise RuleValidationError(
                f"Unknown comparison operator '{op_key}' for '{raw_key}'. Supported: "
                f"{sorted(_OPERATORS)}"
            )
        if op_key == "in":
            if not isinstance(op_value, list):
                raise RuleValidationError(f"The 'in' operator for '{raw_key}' requires a list")
            return f"{path} in {_cel_literal(op_value)}"
        return f"{path} {_OPERATORS[op_key]} {_cel_literal(op_value)}"
    # Implicit equality (e.g. `processes_personal_data: true`,
    # `contract.liability.type: unlimited`).
    return f"{path} == {_cel_literal(raw_value)}"


def compile_rule_when(when: dict[str, Any]) -> CompiledWhen:
    if not isinstance(when, dict) or not when:
        raise RuleValidationError("'when' is required and must be a non-empty mapping")

    presence_clauses: list[str] = []
    seen_prefixes: set[str] = set()
    condition_clauses: list[str] = []
    referenced_paths: list[str] = []

    for raw_key, raw_value in when.items():
        if not isinstance(raw_key, str):
            raise RuleValidationError(f"'when' keys must be strings, got {raw_key!r}")
        path = resolve_path(raw_key)
        referenced_paths.append(path)

        segments = path.split(".")
        for depth in range(1, len(segments) + 1):
            prefix = ".".join(segments[:depth])
            if prefix not in seen_prefixes:
                seen_prefixes.add(prefix)
                presence_clauses.append(f"has({prefix})")

        condition_clauses.append(_compile_condition_clause(path, raw_key, raw_value))

    presence_cel = " && ".join(presence_clauses)
    condition_cel = " && ".join(condition_clauses)

    # Catches any residual CEL syntax error (e.g. a malformed literal) before the rule is
    # ever saved -- "a syntactically invalid rule ... rejected before it's saved,
    # never silently accepted" (#57).
    try:
        _CEL_ENV.compile(presence_cel)
        _CEL_ENV.compile(condition_cel)
    except Exception as exc:  # celpy raises its own exception hierarchy; treat broadly.
        raise RuleValidationError(f"'when' clause failed to compile: {exc}") from exc

    return CompiledWhen(
        presence_cel=presence_cel,
        condition_cel=condition_cel,
        referenced_paths=tuple(sorted(set(referenced_paths))),
    )


def _require_str(doc: dict[str, Any], *keys: str) -> Any:
    node: Any = doc
    for key in keys:
        if not isinstance(node, dict) or key not in node:
            raise RuleValidationError(f"'{'.'.join(keys)}' is required")
        node = node[key]
    return node


def parse_rule_document(doc: dict[str, Any]) -> ParsedRule:
    """Validates and compiles one rule document already parsed into a plain dict (by
    `yaml.safe_load` in `parse_rule_yaml`, or handed in directly as JSON by a future
    no-code rule builder -- the grammar is identical either way)."""
    if not isinstance(doc, dict):
        raise RuleValidationError("A rule document must be a mapping")

    rule_meta = doc.get("rule")
    if not isinstance(rule_meta, dict):
        raise RuleValidationError("'rule' is required and must be a mapping with 'id'/'name'")

    rule_key = rule_meta.get("id")
    if not isinstance(rule_key, str) or not rule_key.strip():
        raise RuleValidationError("'rule.id' is required and must be a non-empty string")

    name = rule_meta.get("name")
    if not isinstance(name, str) or not name.strip():
        raise RuleValidationError("'rule.name' is required and must be a non-empty string")

    when = doc.get("when")
    if not isinstance(when, dict) or not when:
        raise RuleValidationError("'when' is required and must be a non-empty mapping")

    result = doc.get("result")
    if not isinstance(result, dict) or "status" not in result:
        raise RuleValidationError("'result.status' is required")
    result_status = result["status"]
    valid_statuses = {s.value for s in RuleResultStatus}
    if result_status not in valid_statuses:
        raise RuleValidationError(
            f"'result.status' must be one of {sorted(valid_statuses)}, got {result_status!r}"
        )

    severity = doc.get("severity")
    valid_severities = {s.value for s in Severity}
    if severity not in valid_severities:
        raise RuleValidationError(
            f"'severity' must be one of {sorted(valid_severities)}, got {severity!r}"
        )

    approver_role = doc.get("approver_role")
    if approver_role is not None and (
        not isinstance(approver_role, str) or not approver_role.strip()
    ):
        raise RuleValidationError("'approver_role' must be null or a non-empty string")

    # policy-engine.md: "BLOCK has no approver -- it is not overridable without an
    # explicit override action". Symmetrically, an unconditional APPROVE rule has no
    # reviewer to route to either. REVIEW always needs a routable approver_role
    # (ADR-010 §2 / BR-APR-001).
    if result_status == RuleResultStatus.REVIEW.value and not approver_role:
        raise RuleValidationError("'approver_role' is required when result.status is REVIEW")
    if result_status != RuleResultStatus.REVIEW.value and approver_role:
        raise RuleValidationError(
            f"'approver_role' must be null when result.status is {result_status}"
        )

    compiled = compile_rule_when(when)

    return ParsedRule(
        rule_key=rule_key,
        name=name,
        when=when,
        result_status=result_status,
        severity=severity,
        approver_role=approver_role,
        compiled_presence_cel=compiled.presence_cel,
        compiled_condition_cel=compiled.condition_cel,
        referenced_paths=list(compiled.referenced_paths),
    )


def referenced_paths_of(when: dict[str, Any]) -> tuple[str, ...]:
    """Resolves every `when` key to its canonical context path, without compiling CEL --
    a lighter-weight companion to `compile_rule_when` for callers that only need to know
    *which* evaluation-context fields a rule references, not its compiled expressions
    (Phase 5's `RuleEvaluation.evidence_refs` traceability, #126 -- see
    `app.policies.application.compliance_review_service`). `when` here is always an
    already-validated, already-persisted `Rule.when` (compiled once at creation/update
    time via `compile_rule_when`), so every key is guaranteed to resolve without raising."""
    return tuple(sorted({resolve_path(k) for k in when if isinstance(k, str)}))


def parse_rule_yaml(yaml_text: str) -> ParsedRule:
    """The entry point actually used by the create/update-rule endpoints -- policy
    authors submit YAML text (ADR-004: "Policy authors interact with YAML... not raw
    CEL/JSONLogic"), never a pre-parsed JSON body."""
    try:
        doc = yaml.safe_load(yaml_text)
    except yaml.YAMLError as exc:
        raise RuleValidationError(f"Invalid YAML: {exc}") from exc
    return parse_rule_document(doc)
