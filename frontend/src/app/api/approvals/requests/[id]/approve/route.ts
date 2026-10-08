import { NextResponse } from "next/server";

import { ApiError, approveApprovalRequest } from "@/lib/approvals/backend";
import { readAccessToken } from "@/lib/auth/cookies";

/**
 * BFF endpoint for `ApprovalActions`'s Approve button. `justification` is optional here
 * (BR-APR-002's "On approval") — an empty/whitespace-only value is normalized to `null`
 * rather than forwarded as an empty string, matching what the backend's own
 * `ApproveRequestBody.justification` field (`default=None`) actually expects.
 *
 * Surfaces the backend's real conflict messages verbatim (404 not found, 409 already
 * resolved / Decision conflict, 403 role mismatch) — these are meaningful states, not
 * generic errors, per `SupplierDetailActions`'s status-change Route Handler precedent.
 */
export async function POST(
  request: Request,
  { params }: { params: Promise<{ id: string }> },
): Promise<Response> {
  const accessToken = await readAccessToken();
  if (!accessToken) {
    return NextResponse.json({ detail: "Not authenticated." }, { status: 401 });
  }

  const { id } = await params;
  const body = (await request.json().catch(() => null)) as { justification?: unknown } | null;
  const justification =
    typeof body?.justification === "string" && body.justification.trim() !== ""
      ? body.justification
      : null;

  try {
    const approvalRequest = await approveApprovalRequest(accessToken, id, justification);
    return NextResponse.json(approvalRequest);
  } catch (error) {
    if (error instanceof ApiError) {
      return NextResponse.json({ detail: error.detail }, { status: error.status });
    }
    return NextResponse.json({ detail: "Unexpected error." }, { status: 500 });
  }
}
