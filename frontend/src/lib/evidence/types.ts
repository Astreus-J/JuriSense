/**
 * Evidence & Audit domain types mirrored from the backend (source of truth:
 * `backend/app/evidence/api/schemas.py`). Field names are camelCase on this side of the
 * boundary, following `lib/compliance/types.ts`'s convention — `lib/evidence/backend.ts` is
 * the only place that maps the API's snake_case shape into these.
 */

import type { RuleOutcome, Severity } from "@/lib/compliance/types";

/** A `Decision`'s outcome — reuses the same three values `ComplianceReview` has, since a
 * Decision is only ever created once a review (or its approval chain) reaches APPROVE or
 * BLOCK; `REVIEW` never persists on a Decision at rest, but is kept here for parity with
 * `lib/compliance/types.ts`'s `ComplianceReviewStatus` rather than modeling a narrower,
 * two-value union the backend doesn't itself expose. */
export type DecisionStatus = "APPROVE" | "REVIEW" | "BLOCK";

/** FEATURE-6.5: `ACTIVE` is the one effective Decision for its ContractVersion; `SUPERSEDED`
 * is historical (a later re-evaluation or manual review replaced it). */
export type DecisionLifecycle = "ACTIVE" | "SUPERSEDED";

export interface PassportDocument {
  documentId: string;
  contentHash: string;
  mimeType: string;
  sizeBytes: number;
}

export interface PassportAiExecution {
  provider: string | null;
  modelName: string | null;
  promptVersion: string | null;
  extractedAt: string | null;
}

export interface PassportPolicyVersion {
  policyVersionId: string;
  policyId: string;
  versionNumber: number;
}

export interface PassportRuleEvaluation {
  ruleEvaluationId: string;
  ruleId: string;
  ruleKey: string;
  ruleName: string;
  // QA review (2026-10-06): typed as the same literal unions `lib/compliance/types.ts`
  // already defines for the identical backend values, instead of a bare `string` that
  // would force an unchecked `as` cast at every render site.
  outcome: RuleOutcome;
  severity: Severity;
  approverRole: string | null;
  rationale: string;
}

export interface PassportReviewer {
  approvalRequestId: string;
  approverRole: string;
  stepNumber: number;
  status: string;
  resolvedBy: string | null;
  resolvedAt: string | null;
}

/** STORY-7.3.1: the full "why was this approved?" narrative for one Decision, assembled
 * fresh on every read from already-immutable records — nothing here is itself persisted. */
export interface DecisionPassport {
  decisionId: string;
  status: DecisionStatus;
  lifecycle: DecisionLifecycle;
  validUntil: string;
  overridden: boolean;
  overrideJustification: string | null;
  supersedesDecisionId: string | null;
  createdAt: string;
  complianceReviewId: string;
  supplierId: string;
  supplierLegalName: string;
  supplierTaxId: string;
  contractId: string;
  contractTitle: string;
  contractVersionId: string;
  contractVersionNumber: number;
  documents: PassportDocument[];
  aiExecution: PassportAiExecution | null;
  policyVersions: PassportPolicyVersion[];
  ruleEvaluations: PassportRuleEvaluation[];
  externalSourcesConsulted: string[];
  reviewers: PassportReviewer[];
  evidencePackageId: string;
  merkleRoot: string;
  evidenceCount: number;
}

/** FEATURE-8.3: the four plain-language outcomes of the public verification check
 * (docs/06-blockchain/verification.md) — "pending" is this product's own addition to the
 * doc's original three (verified/not_found/mismatch), for a submission whose underlying
 * network hasn't finalized yet. */
export type VerificationStatus = "verified" | "mismatch" | "pending" | "not_found";

/** STORY-8.3.1: the ENTIRE public surface of the verification page — deliberately just
 * these fields, never a supplier/contract/organization identifier (see the backend's
 * `verification_service` module docstring for the privacy boundary this shape enforces). */
export interface PublicVerificationResult {
  status: VerificationStatus;
  evidenceHash: string | null;
  provider: string | null;
  confirmedAt: string | null;
  referenceUrl: string | null;
}
