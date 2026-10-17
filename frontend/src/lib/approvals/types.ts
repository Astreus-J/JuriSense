/**
 * Approvals & Decisions domain types mirrored from the backend (source of truth:
 * `backend/app/approvals/api/schemas.py` and `backend/app/approvals/domain/constants.py`).
 *
 * Field names are camelCase on this side of the boundary; `src/lib/approvals/backend.ts`
 * is the only place that maps the API's snake_case shape into these types.
 */

/** `ApprovalRequestStatus` (`backend/app/approvals/domain/constants.py`): immutable once
 * resolved (BR-APR-001) — `approved`/`rejected` never revert to `pending`. */
export const APPROVAL_REQUEST_STATUSES = ["pending", "approved", "rejected"] as const;

export type ApprovalRequestStatus = (typeof APPROVAL_REQUEST_STATUSES)[number];

/**
 * One step of an `ApprovalWorkflow` instantiated for a `ComplianceReview` (docs/03-domain/
 * approvals.md). `approverRole` is whichever of the 10 `Role` values the triggering `Rule`
 * named — it is a plain string here (not the `Role` union) because nothing in this context
 * guarantees it always is one of the 10 (a rule could, in principle, name a role that was
 * since removed); render it defensively (`isRole` guard) rather than assuming.
 *
 * There is deliberately no supplier/contract/review name on this object — the API doesn't
 * return one (`ApprovalRequestResponse` only carries `compliance_review_id`); the `/approvals`
 * screen links out to `/compliance/reviews/{complianceReviewId}` for that context instead of
 * duplicating it here.
 */
export interface ApprovalRequest {
  id: string;
  organizationId: string;
  complianceReviewId: string;
  approvalWorkflowId: string;
  approverRole: string;
  stepNumber: number;
  status: ApprovalRequestStatus;
  justification: string | null;
  resolvedBy: string | null;
  resolvedAt: string | null;
  requestedAt: string;
  createdAt: string;
  updatedAt: string;
}
