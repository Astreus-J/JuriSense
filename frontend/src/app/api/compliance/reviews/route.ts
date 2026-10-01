import { NextResponse } from "next/server";

import { readAccessToken } from "@/lib/auth/cookies";
import { ApiError, listComplianceReviews, triggerComplianceReview } from "@/lib/compliance/backend";

interface TriggerReviewBody {
  contractVersionId?: unknown;
}

/**
 * BFF endpoint for `TriggerComplianceReviewButton` (`POST`, #62/#123) and for discovering a
 * `ContractVersion`'s review history (`GET`). Mirrors `src/app/api/suppliers/[id]/recheck/
 * route.ts`'s auth-cookie + `ApiError` passthrough shape exactly.
 */
export async function POST(request: Request): Promise<Response> {
  const accessToken = await readAccessToken();
  if (!accessToken) {
    return NextResponse.json({ detail: "Not authenticated." }, { status: 401 });
  }

  const body = (await request.json().catch(() => null)) as TriggerReviewBody | null;
  if (typeof body?.contractVersionId !== "string") {
    return NextResponse.json({ detail: "A contract version id is required." }, { status: 400 });
  }

  try {
    const review = await triggerComplianceReview(accessToken, body.contractVersionId);
    return NextResponse.json(review, { status: 201 });
  } catch (error) {
    if (error instanceof ApiError) {
      return NextResponse.json({ detail: error.detail }, { status: error.status });
    }
    return NextResponse.json({ detail: "Unexpected error." }, { status: 500 });
  }
}

export async function GET(request: Request): Promise<Response> {
  const accessToken = await readAccessToken();
  if (!accessToken) {
    return NextResponse.json({ detail: "Not authenticated." }, { status: 401 });
  }

  const contractVersionId = new URL(request.url).searchParams.get("contractVersionId");
  if (!contractVersionId) {
    return NextResponse.json({ detail: "A contract version id is required." }, { status: 400 });
  }

  try {
    const reviews = await listComplianceReviews(accessToken, contractVersionId);
    return NextResponse.json(reviews);
  } catch (error) {
    if (error instanceof ApiError) {
      return NextResponse.json({ detail: error.detail }, { status: error.status });
    }
    return NextResponse.json({ detail: "Unexpected error." }, { status: 500 });
  }
}
