import "server-only";

import { ApiError, request } from "@/lib/auth/backend";
import type {
  ComplianceReview,
  ComplianceReviewDetail,
  ComplianceReviewStatus,
  EvidenceRef,
  Risk,
  RuleEvaluationRecord,
  RuleOutcome,
  Severity,
} from "./types";

export { ApiError };

const UUID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/**
 * Same guard as `lib/suppliers/backend.ts`'s `assertValidSupplierId`/`lib/contracts/
 * backend.ts`'s `assertValidId`, applied to every id this module interpolates into a backend
 * URL path — see `lib/suppliers/backend.ts`'s docstring for the confirmed-live confused-
 * deputy bug this prevents. Every backend id here is a UUID; reject anything else before it
 * ever reaches a template string.
 */
function assertValidId(id: string, label: string): void {
  if (!UUID_PATTERN.test(id)) {
    throw new ApiError(400, `Invalid ${label}.`);
  }
}

/**
 * Thin server-only client for the Compliance Reviews API
 * (`backend/app/policies/api/routes.py`'s `compliance_router`), following `lib/suppliers/
 * backend.ts`'s/`lib/contracts/backend.ts`'s exact pattern. Never imported by a Client
 * Component — `server-only` turns an accidental client import into a build error; mutations
 * from Client Components go through the `/api/compliance/*` Route Handlers instead.
 */

interface RawComplianceReviewResponse {
  id: string;
  organization_id: string;
  contract_version_id: string;
  policy_version_ids: string[];
  status: string;
  started_at: string;
  completed_at: string | null;
}

interface RawRuleEvaluationRecordResponse {
  id: string;
  compliance_review_id: string;
  rule_id: string;
  rule_key: string;
  rule_name: string;
  outcome: string;
  severity: string;
  approver_role: string | null;
  rationale: string;
  evidence_refs: EvidenceRef[];
  created_at: string;
}

interface RawRiskResponse {
  id: string;
  compliance_review_id: string;
  category: string;
  description: string;
  severity: string;
  evidence_refs: EvidenceRef[];
  created_at: string;
}

interface RawComplianceReviewDetailResponse {
  review: RawComplianceReviewResponse;
  rule_evaluations: RawRuleEvaluationRecordResponse[];
  risks: RawRiskResponse[];
}

function toComplianceReview(raw: RawComplianceReviewResponse): ComplianceReview {
  return {
    id: raw.id,
    organizationId: raw.organization_id,
    contractVersionId: raw.contract_version_id,
    policyVersionIds: raw.policy_version_ids,
    status: raw.status as ComplianceReviewStatus,
    startedAt: raw.started_at,
    completedAt: raw.completed_at,
  };
}

function toRuleEvaluationRecord(raw: RawRuleEvaluationRecordResponse): RuleEvaluationRecord {
  return {
    id: raw.id,
    complianceReviewId: raw.compliance_review_id,
    ruleId: raw.rule_id,
    ruleKey: raw.rule_key,
    ruleName: raw.rule_name,
    outcome: raw.outcome as RuleOutcome,
    severity: raw.severity as Severity,
    approverRole: raw.approver_role,
    rationale: raw.rationale,
    evidenceRefs: raw.evidence_refs,
    createdAt: raw.created_at,
  };
}

function toRisk(raw: RawRiskResponse): Risk {
  return {
    id: raw.id,
    complianceReviewId: raw.compliance_review_id,
    category: raw.category,
    description: raw.description,
    severity: raw.severity as Severity,
    evidenceRefs: raw.evidence_refs,
    createdAt: raw.created_at,
  };
}

/** CMP-*: triggers a real, synchronous `ComplianceReview` — pools every currently-published
 * `PolicyVersion` in the caller's organization and evaluates them against the given
 * `ContractVersion`. No polling needed: the backend returns the terminal result directly. */
export async function triggerComplianceReview(
  accessToken: string,
  contractVersionId: string,
): Promise<ComplianceReview> {
  assertValidId(contractVersionId, "contract version id");
  const raw = await request<RawComplianceReviewResponse>("/compliance/reviews", {
    method: "POST",
    accessToken,
    body: JSON.stringify({ contract_version_id: contractVersionId }),
  });
  return toComplianceReview(raw);
}

/** #62: the full explainability read-model for the results screen — one `ComplianceReview`
 * with every `RuleEvaluation` it ran (not just the ones that triggered a `Risk`) and every
 * `Risk` it recorded. */
export async function getComplianceReview(
  accessToken: string,
  reviewId: string,
): Promise<ComplianceReviewDetail> {
  assertValidId(reviewId, "compliance review id");
  const raw = await request<RawComplianceReviewDetailResponse>(
    `/compliance/reviews/${reviewId}`,
    { accessToken },
  );
  return {
    review: toComplianceReview(raw.review),
    ruleEvaluations: raw.rule_evaluations.map(toRuleEvaluationRecord),
    risks: raw.risks.map(toRisk),
  };
}

/** #62's review-history read-model: every `ComplianceReview` ever run for a given
 * `ContractVersion`, oldest-first (matching the API's own order) — `[]` if none have run
 * yet, which is a legitimate "not reviewed" state, not an error. */
export async function listComplianceReviews(
  accessToken: string,
  contractVersionId: string,
): Promise<ComplianceReview[]> {
  assertValidId(contractVersionId, "contract version id");
  const raw = await request<RawComplianceReviewResponse[]>(
    `/compliance/reviews?contract_version_id=${encodeURIComponent(contractVersionId)}`,
    { accessToken },
  );
  return raw.map(toComplianceReview);
}
