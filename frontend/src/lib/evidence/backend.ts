import "server-only";

import { ApiError, request } from "@/lib/auth/backend";
import type { RuleOutcome, Severity } from "@/lib/compliance/types";
import type {
  DecisionLifecycle,
  DecisionPassport,
  DecisionStatus,
  PassportAiExecution,
  PassportDocument,
  PassportPolicyVersion,
  PassportReviewer,
  PassportRuleEvaluation,
  PublicVerificationResult,
  VerificationStatus,
} from "./types";

export { ApiError };

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** Same guard as `lib/compliance/backend.ts`'s `assertValidId` — see its docstring for the
 * confused-deputy bug this prevents. Every backend id here is a UUID. */
function assertValidId(id: string, label: string): void {
  if (!UUID_PATTERN.test(id)) {
    throw new ApiError(400, `Invalid ${label}.`);
  }
}

/**
 * Thin server-only client for the Decision Passport API
 * (`backend/app/evidence/api/routes.py`'s `decision_passport_router`), following
 * `lib/compliance/backend.ts`'s exact pattern. Never imported by a Client Component.
 */

interface RawPassportDocumentResponse {
  document_id: string;
  content_hash: string;
  mime_type: string;
  size_bytes: number;
}

interface RawPassportAiExecutionResponse {
  provider: string | null;
  model_name: string | null;
  prompt_version: string | null;
  extracted_at: string | null;
}

interface RawPassportPolicyVersionResponse {
  policy_version_id: string;
  policy_id: string;
  version_number: number;
}

interface RawPassportRuleEvaluationResponse {
  rule_evaluation_id: string;
  rule_id: string;
  rule_key: string;
  rule_name: string;
  outcome: string;
  severity: string;
  approver_role: string | null;
  rationale: string;
}

interface RawPassportReviewerResponse {
  approval_request_id: string;
  approver_role: string;
  step_number: number;
  status: string;
  resolved_by: string | null;
  resolved_at: string | null;
}

interface RawDecisionPassportResponse {
  decision_id: string;
  status: string;
  lifecycle: string;
  valid_until: string;
  overridden: boolean;
  override_justification: string | null;
  supersedes_decision_id: string | null;
  created_at: string;
  compliance_review_id: string;
  supplier_id: string;
  supplier_legal_name: string;
  supplier_tax_id: string;
  contract_id: string;
  contract_title: string;
  contract_version_id: string;
  contract_version_number: number;
  documents: RawPassportDocumentResponse[];
  ai_execution: RawPassportAiExecutionResponse | null;
  policy_versions: RawPassportPolicyVersionResponse[];
  rule_evaluations: RawPassportRuleEvaluationResponse[];
  external_sources_consulted: string[];
  reviewers: RawPassportReviewerResponse[];
  evidence_package_id: string;
  merkle_root: string;
  evidence_count: number;
}

function toPassportDocument(raw: RawPassportDocumentResponse): PassportDocument {
  return {
    documentId: raw.document_id,
    contentHash: raw.content_hash,
    mimeType: raw.mime_type,
    sizeBytes: raw.size_bytes,
  };
}

function toPassportAiExecution(raw: RawPassportAiExecutionResponse): PassportAiExecution {
  return {
    provider: raw.provider,
    modelName: raw.model_name,
    promptVersion: raw.prompt_version,
    extractedAt: raw.extracted_at,
  };
}

function toPassportPolicyVersion(raw: RawPassportPolicyVersionResponse): PassportPolicyVersion {
  return {
    policyVersionId: raw.policy_version_id,
    policyId: raw.policy_id,
    versionNumber: raw.version_number,
  };
}

function toPassportRuleEvaluation(raw: RawPassportRuleEvaluationResponse): PassportRuleEvaluation {
  return {
    ruleEvaluationId: raw.rule_evaluation_id,
    ruleId: raw.rule_id,
    ruleKey: raw.rule_key,
    ruleName: raw.rule_name,
    outcome: raw.outcome as RuleOutcome,
    severity: raw.severity as Severity,
    approverRole: raw.approver_role,
    rationale: raw.rationale,
  };
}

function toPassportReviewer(raw: RawPassportReviewerResponse): PassportReviewer {
  return {
    approvalRequestId: raw.approval_request_id,
    approverRole: raw.approver_role,
    stepNumber: raw.step_number,
    status: raw.status,
    resolvedBy: raw.resolved_by,
    resolvedAt: raw.resolved_at,
  };
}

function toDecisionPassport(raw: RawDecisionPassportResponse): DecisionPassport {
  return {
    decisionId: raw.decision_id,
    status: raw.status as DecisionStatus,
    lifecycle: raw.lifecycle as DecisionLifecycle,
    validUntil: raw.valid_until,
    overridden: raw.overridden,
    overrideJustification: raw.override_justification,
    supersedesDecisionId: raw.supersedes_decision_id,
    createdAt: raw.created_at,
    complianceReviewId: raw.compliance_review_id,
    supplierId: raw.supplier_id,
    supplierLegalName: raw.supplier_legal_name,
    supplierTaxId: raw.supplier_tax_id,
    contractId: raw.contract_id,
    contractTitle: raw.contract_title,
    contractVersionId: raw.contract_version_id,
    contractVersionNumber: raw.contract_version_number,
    documents: raw.documents.map(toPassportDocument),
    aiExecution: raw.ai_execution ? toPassportAiExecution(raw.ai_execution) : null,
    policyVersions: raw.policy_versions.map(toPassportPolicyVersion),
    ruleEvaluations: raw.rule_evaluations.map(toPassportRuleEvaluation),
    externalSourcesConsulted: raw.external_sources_consulted,
    reviewers: raw.reviewers.map(toPassportReviewer),
    evidencePackageId: raw.evidence_package_id,
    merkleRoot: raw.merkle_root,
    evidenceCount: raw.evidence_count,
  };
}

/** STORY-7.3.1: the full Decision Passport read-model for one Decision. A Decision in
 * another organization, and a Decision with no EvidencePackage yet, both 404 — see the
 * route's own docstring (ADR-003: indistinguishable by design). */
export async function getDecisionPassport(
  accessToken: string,
  decisionId: string,
): Promise<DecisionPassport> {
  assertValidId(decisionId, "decision id");
  const raw = await request<RawDecisionPassportResponse>(`/decisions/${decisionId}/passport`, {
    accessToken,
  });
  return toDecisionPassport(raw);
}

interface RawPublicVerificationResponse {
  status: string;
  evidence_hash: string | null;
  provider: string | null;
  confirmed_at: string | null;
  reference_url: string | null;
}

/** STORY-8.3.1: the public, unauthenticated verification check
 * (`GET /api/public/verify`) — no `accessToken`, by design: this is the one backend call in
 * the app meant to work for a visitor with no session at all. Never throws for a malformed
 * or unknown `reference` — the route always answers 200 with `status: "not_found"` for
 * those, matching this function's own "never raises" contract for anything less than a
 * genuine network/server failure. */
export async function verifyPublicReference(reference: string): Promise<PublicVerificationResult> {
  const raw = await request<RawPublicVerificationResponse>(
    `/public/verify?ref=${encodeURIComponent(reference)}`,
  );
  return {
    status: raw.status as VerificationStatus,
    evidenceHash: raw.evidence_hash,
    provider: raw.provider,
    confirmedAt: raw.confirmed_at,
    referenceUrl: raw.reference_url,
  };
}
