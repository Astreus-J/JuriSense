/**
 * Policy & Compliance domain types mirrored from the backend (source of truth:
 * `backend/app/policies/api/schemas.py` and `backend/app/policies/domain/constants.py`).
 *
 * Field names are camelCase on this side of the boundary; `src/lib/policies/backend.ts`
 * is the only place that maps the API's snake_case shape into these types.
 */

/**
 * Container-level lifecycle (`backend/app/policies/domain/constants.py`'s `PolicyStatus`):
 * a Policy becomes `published` the moment its first `PolicyVersion` is published, and
 * stays `published` across subsequent republishes. `archived` has no transition into it
 * yet anywhere in the product (no action in this screen offers it) — it only exists here
 * so a policy a backend operator archived directly still renders a real, labeled status
 * instead of falling through to an `undefined` lookup.
 */
export const POLICY_STATUSES = ["draft", "published", "archived"] as const;

export type PolicyStatus = (typeof POLICY_STATUSES)[number];

export const POLICY_STATUS_LABELS: Record<PolicyStatus, string> = {
  draft: "Draft",
  published: "Published",
  archived: "Archived",
};

export interface Policy {
  id: string;
  organizationId: string;
  name: string;
  status: PolicyStatus;
  createdAt: string;
  updatedAt: string;
}

/**
 * A `PolicyVersion` is `draft` (its Rules are mutable) until published, at which point
 * every Rule it owns is frozen permanently (BR-POL-001) — there is no transition back to
 * draft; editing a published version always means creating a new draft version instead
 * (`docs/03-domain/policy-engine.md` "Rule lifecycle").
 */
export const POLICY_VERSION_STATUSES = ["draft", "published"] as const;

export type PolicyVersionStatus = (typeof POLICY_VERSION_STATUSES)[number];

export const POLICY_VERSION_STATUS_LABELS: Record<PolicyVersionStatus, string> = {
  draft: "Draft",
  published: "Published",
};

export interface PolicyVersion {
  id: string;
  policyId: string;
  versionNumber: number;
  status: PolicyVersionStatus;
  /** Only one version per policy is ever `true` at a time (BR-POL-002). */
  isCurrent: boolean;
  publishedAt: string | null;
  publishedBy: string | null;
  createdAt: string;
}

/** The *authored* outcome a Rule's `result.status` carries in the DSL — what happens when
 * its `when` condition matches (`docs/03-domain/policy-engine.md` "Rule DSL"). */
export const RULE_RESULT_STATUSES = ["APPROVE", "REVIEW", "BLOCK"] as const;

export type RuleResultStatus = (typeof RULE_RESULT_STATUSES)[number];

export const RULE_RESULT_STATUS_LABELS: Record<RuleResultStatus, string> = {
  APPROVE: "Approve",
  REVIEW: "Review",
  BLOCK: "Block",
};

/** Drives required-approver tie-breaking among simultaneous REVIEW rules and reviewer-
 * queue prioritization — never the APPROVE/REVIEW/BLOCK aggregation itself
 * (`docs/03-domain/policy-engine.md` "Severity & escalation"). */
export const SEVERITIES = ["critical", "high", "medium", "low"] as const;

export type Severity = (typeof SEVERITIES)[number];

export const SEVERITY_LABELS: Record<Severity, string> = {
  critical: "Critical",
  high: "High",
  medium: "Medium",
  low: "Low",
};

/**
 * One executable condition within a `PolicyVersion`. `when` is the raw, already-validated
 * `when:` mapping exactly as authored in YAML (a flat `dotted.path -> literal-or-{op:
 * value}` mapping — `backend/app/policies/domain/rule_dsl.py`'s `compile_rule_when`),
 * never the compiled CEL — the two `compiled*Cel` fields carry that separately, for
 * display/debugging only, never re-submitted by this app.
 */
export interface Rule {
  id: string;
  policyVersionId: string;
  ruleKey: string;
  name: string;
  when: Record<string, unknown>;
  resultStatus: RuleResultStatus;
  severity: Severity;
  approverRole: string | null;
  compiledPresenceCel: string;
  compiledConditionCel: string;
  isFrozen: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface CreatePolicyResult {
  policy: Policy;
  initialVersion: PolicyVersion;
}

const HUMAN_OPERATORS: Record<string, string> = {
  eq: "=",
  ne: "!=",
  gt: ">",
  gte: ">=",
  lt: "<",
  lte: "<=",
  in: "in",
};

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function formatWhenValue(value: unknown): string {
  if (typeof value === "string") return value;
  if (Array.isArray(value)) return `[${value.map(formatWhenValue).join(", ")}]`;
  return String(value);
}

/**
 * Renders a `when` clause as the human-readable condition text the product's "WHY,
 * EVIDENCE, POLICY, SOURCE" explainability principle (ADR-010) calls for, mirroring
 * `backend/app/policies/domain/rule_dsl.py`'s `describe_when` so a rule reads the same way
 * here as it does in a `RuleEvaluation.rationale` elsewhere in the product — e.g.
 * `{"contract.value.brl": {"gte": 250000}}` becomes `contract.value.brl >= 250000`,
 * never the raw mapping syntax.
 */
export function describeWhen(when: Record<string, unknown>): string {
  const clauses = Object.entries(when).map(([key, value]) => {
    if (isPlainObject(value) && Object.keys(value).length === 1) {
      const [opKey, opValue] = Object.entries(value)[0];
      const op = HUMAN_OPERATORS[opKey] ?? opKey;
      return `${key} ${op} ${formatWhenValue(opValue)}`;
    }
    return `${key} = ${formatWhenValue(value)}`;
  });
  return clauses.join(" AND ");
}
