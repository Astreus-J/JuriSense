import "server-only";

import { ApiError, request } from "@/lib/auth/backend";
import type { ApprovalRequest, ApprovalRequestStatus } from "./types";

export { ApiError };

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/**
 * Same guard as `lib/suppliers/backend.ts`'s `assertValidSupplierId`/`lib/compliance/
 * backend.ts`'s `assertValidId`, applied to every id this module interpolates into a
 * backend URL path — see `lib/suppliers/backend.ts`'s docstring for the confirmed-live
 * confused-deputy bug this prevents. Every backend id here is a UUID; reject anything else
 * before it ever reaches a template string.
 */
function assertValidId(id: string, label: string): void {
  if (!UUID_PATTERN.test(id)) {
    throw new ApiError(400, `Invalid ${label}.`);
  }
}

/**
 * Thin server-only client for the Approvals & Decisions API
 * (`backend/app/approvals/api/routes.py`), following `lib/suppliers/backend.ts`'s/
 * `lib/compliance/backend.ts`'s exact pattern. Never imported by a Client Component —
 * `server-only` turns an accidental client import into a build error; mutations from
 * Client Components go through the `/api/approvals/*` Route Handlers instead.
 */

interface RawApprovalRequestResponse {
  id: string;
  organization_id: string;
  compliance_review_id: string;
  approval_workflow_id: string;
  approver_role: string;
  step_number: number;
  status: string;
  justification: string | null;
  resolved_by: string | null;
  resolved_at: string | null;
  requested_at: string;
  created_at: string;
  updated_at: string;
}

function toApprovalRequest(raw: RawApprovalRequestResponse): ApprovalRequest {
  return {
    id: raw.id,
    organizationId: raw.organization_id,
    complianceReviewId: raw.compliance_review_id,
    approvalWorkflowId: raw.approval_workflow_id,
    approverRole: raw.approver_role,
    stepNumber: raw.step_number,
    status: raw.status as ApprovalRequestStatus,
    justification: raw.justification,
    resolvedBy: raw.resolved_by,
    resolvedAt: raw.resolved_at,
    requestedAt: raw.requested_at,
    createdAt: raw.created_at,
    updatedAt: raw.updated_at,
  };
}

/**
 * The `/approvals` screen's main data source: every `pending` `ApprovalRequest` in the
 * caller's organization routed to the caller's own role, across every `ComplianceReview`
 * (`GET /approvals/requests/pending`, added specifically for this screen — there was
 * previously no cross-review "my inbox" endpoint, only `listRequestsForReview`'s
 * per-review list below).
 */
export async function listPendingApprovalRequests(
  accessToken: string,
): Promise<ApprovalRequest[]> {
  const raw = await request<RawApprovalRequestResponse[]>("/approvals/requests/pending", {
    accessToken,
  });
  return raw.map(toApprovalRequest);
}

/**
 * APR-*: resolves a pending `ApprovalRequest` as approved. `justification` is optional on
 * approval, unlike `rejectApprovalRequest`'s mandatory one (docs/03-domain/approvals.md
 * "On approval"/"On rejection"). 404 (not found/cross-tenant), 409 (already resolved, or a
 * `Decision`/override-supersession conflict), 403 (the caller's own role no longer matches
 * `approverRole` — can happen even though `/requests/pending` only ever lists requests that
 * matched at load time) all surface as a normal `ApiError` for the caller to handle.
 */
export async function approveApprovalRequest(
  accessToken: string,
  requestId: string,
  justification: string | null,
): Promise<ApprovalRequest> {
  assertValidId(requestId, "approval request id");
  const raw = await request<RawApprovalRequestResponse>(
    `/approvals/requests/${requestId}/approve`,
    {
      method: "POST",
      accessToken,
      body: JSON.stringify({ justification }),
    },
  );
  return toApprovalRequest(raw);
}

/**
 * BR-APR-002: `justification` is mandatory and non-empty here — the backend
 * (`EmptyJustificationError`) is the authority on that; this client forwards whatever the
 * `/api/approvals/requests/[id]/reject` Route Handler gives it rather than re-validating.
 * Same error shapes as `approveApprovalRequest`, plus a 422 for an empty justification.
 */
export async function rejectApprovalRequest(
  accessToken: string,
  requestId: string,
  justification: string,
): Promise<ApprovalRequest> {
  assertValidId(requestId, "approval request id");
  const raw = await request<RawApprovalRequestResponse>(
    `/approvals/requests/${requestId}/reject`,
    {
      method: "POST",
      accessToken,
      body: JSON.stringify({ justification }),
    },
  );
  return toApprovalRequest(raw);
}
