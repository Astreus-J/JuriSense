import { NextResponse } from "next/server";

import { ApiError, rejectApprovalRequest } from "@/lib/approvals/backend";
import { readAccessToken } from "@/lib/auth/cookies";

/**
 * BFF endpoint for `ApprovalActions`'s Reject button. `justification` is mandatory here
 * (BR-APR-002's "On rejection", `EmptyJustificationError`) — the backend is the authority
 * on that, not this handler, so the raw value is forwarded as-is. A literal empty string
 * trips the backend's own Pydantic `min_length=1` constraint (not `EmptyJustificationError`
 * itself), returning FastAPI's array-shaped validation-error `detail`; `parseErrorDetail`
 * in `lib/auth/backend.ts` unwraps that shape too, so either rejection path surfaces a
 * real, specific message instead of a generic one.
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
  if (typeof body?.justification !== "string") {
    return NextResponse.json(
      { detail: "A justification is required to reject this request." },
      { status: 400 },
    );
  }

  try {
    const approvalRequest = await rejectApprovalRequest(accessToken, id, body.justification);
    return NextResponse.json(approvalRequest);
  } catch (error) {
    if (error instanceof ApiError) {
      return NextResponse.json({ detail: error.detail }, { status: error.status });
    }
    return NextResponse.json({ detail: "Unexpected error." }, { status: 500 });
  }
}
