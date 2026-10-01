import { NextResponse } from "next/server";

import { readAccessToken } from "@/lib/auth/cookies";
import { ApiError, getComplianceReview } from "@/lib/compliance/backend";

/**
 * BFF endpoint for the compliance review detail read-model. The results screen itself (a
 * Server Component) calls `getComplianceReview` directly and never hits this route — it
 * exists for parity with every other context's `/api/<context>/<id>` detail route, in case a
 * future Client Component needs to re-fetch (e.g. a manual refresh action).
 */
export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> },
): Promise<Response> {
  const accessToken = await readAccessToken();
  if (!accessToken) {
    return NextResponse.json({ detail: "Not authenticated." }, { status: 401 });
  }

  const { id } = await params;

  try {
    const detail = await getComplianceReview(accessToken, id);
    return NextResponse.json(detail);
  } catch (error) {
    if (error instanceof ApiError) {
      return NextResponse.json({ detail: error.detail }, { status: error.status });
    }
    return NextResponse.json({ detail: "Unexpected error." }, { status: 500 });
  }
}
