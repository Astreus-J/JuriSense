import type { Rule } from "./types";

/**
 * The placeholder shown in an empty "Add rule" form — the LEGAL-008 example from
 * `docs/03-domain/policy-engine.md` ("Rule DSL"), chosen over the simpler BLOCK examples
 * there because it exercises every field a policy author needs to see at a glance
 * (`approver_role` included, not `null`).
 */
export const RULE_YAML_PLACEHOLDER = `rule:
  id: LEGAL-008
  name: Unlimited Liability Requires Legal Review
when:
  contract.liability.type: unlimited
result:
  status: REVIEW
severity: high
approver_role: legal`;

/**
 * QA review (2026-10-08): the previous `/^[A-Za-z0-9_.-]+$/` pattern left a string like
 * a CNAE code ("4711301", `supplier.cnae_code`'s real-world shape) or an ISO date
 * ("2026-01-01") unquoted. PyYAML's default resolver (what the backend's `yaml.safe_load`
 * actually uses) reads an unquoted all-digit token as an `int` and an unquoted
 * `YYYY-MM-DD` token as a `datetime.date` -- silently changing a rule's compiled CEL
 * expression (`rule_dsl._compile_condition_clause` takes a different, usually-broken,
 * branch for a numeric/date value than for the string the rule was actually authored
 * against) on a no-op edit that never touched that line. Requiring the token to START
 * with a letter rules out every case PyYAML's int/float/timestamp resolvers can match
 * (all of them require a leading digit or sign), so quoting is the conservative default
 * and unquoting only happens for tokens no YAML resolver could reinterpret.
 */
const SAFE_UNQUOTED = /^[A-Za-z][A-Za-z0-9_.-]*$/;
const YAML_RESERVED_WORDS = new Set([
  "null",
  "~",
  "true",
  "false",
  "yes",
  "no",
  "on",
  "off",
  "nan",
  "inf",
  "-inf",
]);

function yamlScalar(value: unknown): string {
  if (value === null || value === undefined) return "null";
  if (typeof value === "boolean") return value ? "true" : "false";
  if (typeof value === "number") return String(value);
  const text = String(value);
  const isSafeUnquoted = SAFE_UNQUOTED.test(text) && !YAML_RESERVED_WORDS.has(text.toLowerCase());
  return isSafeUnquoted ? text : JSON.stringify(text);
}

/** `when` values are always either a plain scalar, or a single-key `{op: value}` mapping
 * (`compile_rule_when`'s grammar) — rendered as YAML's flow-mapping/flow-sequence syntax
 * so the whole clause stays on one line, matching how a human author would write it. */
function yamlWhenValue(value: unknown): string {
  if (Array.isArray(value)) {
    return `[${value.map(yamlScalar).join(", ")}]`;
  }
  if (typeof value === "object" && value !== null) {
    const entries = Object.entries(value as Record<string, unknown>);
    return `{ ${entries.map(([k, v]) => `${k}: ${yamlWhenValue(v)}`).join(", ")} }`;
  }
  return yamlScalar(value);
}

/**
 * Reconstructs editable rule YAML from a `Rule`'s already-parsed fields. The backend never
 * stores the original YAML text a rule was authored as (`RuleResponse` has no `yaml`
 * field — only the parsed/compiled result), so editing an existing rule means
 * re-deriving an equivalent document from `when`/`resultStatus`/`severity`/`approverRole`
 * rather than displaying the author's original formatting/comments. This is a faithful
 * re-serialization of the same grammar `rule_dsl.parse_rule_document` accepts, not a
 * lossy approximation — submitting it unchanged round-trips to the identical compiled
 * rule.
 */
export function buildRuleYamlDraft(rule: Rule): string {
  const lines = [
    "rule:",
    `  id: ${yamlScalar(rule.ruleKey)}`,
    `  name: ${yamlScalar(rule.name)}`,
    "when:",
    ...Object.entries(rule.when).map(([key, value]) => `  ${key}: ${yamlWhenValue(value)}`),
    "result:",
    `  status: ${rule.resultStatus}`,
    `severity: ${rule.severity}`,
    `approver_role: ${rule.approverRole ? yamlScalar(rule.approverRole) : "null"}`,
  ];
  return lines.join("\n");
}
