/**
 * Policy & Compliance domain types mirrored from the backend (source of truth:
 * `backend/app/policies/api/schemas.py`).
 *
 * Field names are camelCase on this side of the boundary, following the same convention as
 * `lib/suppliers/types.ts`/`lib/contracts/types.ts` — `lib/compliance/backend.ts` is the
 * only place that maps the API's snake_case shape into these types.
 *
 * `EvidenceRef` is the one exception, for the same reason `SupplierProfile.corporateStructure`
 * and `ContractFields` stay in their original shape: each ref is a dynamic, schema-flexible
 * blob (one of two discriminated shapes on the wire — see `backend/app/policies/api/schemas.py`'s
 * `RuleEvaluationRecordResponse.evidence_refs` docstring and this story's brief), not a flat
 * API resource. `lib/compliance/evidence.ts`'s `describeEvidenceRef` is the only place that
 * reads its (snake_case) keys for display.
 */

/** A `ComplianceReview`'s terminal decision (BR-POL/`docs/03-domain/policy-engine.md`'s
 * decision-aggregation algorithm, ADR-010). `"in_progress"` is never externally observable —
 * `trigger_review` runs synchronously — so there is no transient status to model here. */
export const COMPLIANCE_REVIEW_STATUSES = ["APPROVE", "REVIEW", "BLOCK"] as const;

export type ComplianceReviewStatus = (typeof COMPLIANCE_REVIEW_STATUSES)[number];

export const COMPLIANCE_REVIEW_STATUS_LABELS: Record<ComplianceReviewStatus, string> = {
  APPROVE: "Approved",
  REVIEW: "Review required",
  BLOCK: "Blocked",
};

/** A single `RuleEvaluation`'s outcome. `NOT_APPLICABLE` means the rule's presence condition
 * didn't match this contract's context at all (e.g. a finance-threshold rule when the
 * contract has no value field) — distinct from `PASS`, which means the condition was
 * evaluated and didn't trigger. */
export const RULE_OUTCOMES = ["PASS", "REVIEW", "BLOCK", "NOT_APPLICABLE"] as const;

export type RuleOutcome = (typeof RULE_OUTCOMES)[number];

export const RULE_OUTCOME_LABELS: Record<RuleOutcome, string> = {
  PASS: "Pass",
  REVIEW: "Review required",
  BLOCK: "Blocked",
  NOT_APPLICABLE: "Not applicable",
};

export const SEVERITIES = ["critical", "high", "medium", "low"] as const;

export type Severity = (typeof SEVERITIES)[number];

export const SEVERITY_LABELS: Record<Severity, string> = {
  critical: "Critical",
  high: "High",
  medium: "Medium",
  low: "Low",
};

/** One evidence citation backing a `RuleEvaluation`/`Risk` — either a
 * `contract_extracted_field` ref (`context_path`, `contract_version_id`, `document_id`,
 * `page`, `text_span`) or a `supplier_profile` ref (`context_path`, `supplier_id`,
 * `supplier_profile_id`, `supplier_check_id`). `context_path` is always present and is a
 * legitimate SOURCE citation on its own even when the richer fields are absent. Kept as a
 * structural pass-through (snake_case keys, untransformed) — see this file's module
 * docstring. */
export type EvidenceRef = Record<string, unknown>;

export interface ComplianceReview {
  id: string;
  organizationId: string;
  contractVersionId: string;
  /** Every currently-published `PolicyVersion` pooled into this review (ADR-010's
   * multi-policy pooling design) — the UI only needs the count, not the versions themselves. */
  policyVersionIds: string[];
  status: ComplianceReviewStatus;
  startedAt: string;
  completedAt: string | null;
}

export interface RuleEvaluationRecord {
  id: string;
  complianceReviewId: string;
  ruleId: string;
  /** The author-facing rule id, e.g. `"FIN-003"`. */
  ruleKey: string;
  ruleName: string;
  outcome: RuleOutcome;
  severity: Severity;
  /** Non-null only when `outcome === "REVIEW"`. */
  approverRole: string | null;
  /** Human-readable condition text, e.g. `"Rule 'FIN-003' condition matched:
   * contract.value.brl >= 250000."` — the WHY half of WHY/EVIDENCE/POLICY/SOURCE. */
  rationale: string;
  evidenceRefs: EvidenceRef[];
  createdAt: string;
}

/** One `Risk` per `RuleEvaluation` whose outcome was `REVIEW` or `BLOCK` — never for
 * `PASS`/`NOT_APPLICABLE`. Today `category`/`description` always mirror the triggering
 * rule's `rule_key`/`rationale` 1:1 (see `RiskResponse`'s docstring in
 * `backend/app/policies/api/schemas.py`), but the two are modeled as their own entity on the
 * wire, so this type keeps them distinct rather than assuming that will always hold. */
export interface Risk {
  id: string;
  complianceReviewId: string;
  category: string;
  description: string;
  severity: Severity;
  evidenceRefs: EvidenceRef[];
  createdAt: string;
}

export interface ComplianceReviewDetail {
  review: ComplianceReview;
  /** Every rule the engine evaluated, not just the ones that triggered a `Risk` — the
   * full-transparency POLICY list this story's results screen must render in its entirety. */
  ruleEvaluations: RuleEvaluationRecord[];
  risks: Risk[];
}
