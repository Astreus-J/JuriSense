import { NextResponse } from "next/server";

import { readAccessToken } from "@/lib/auth/cookies";
import { ApiError, publishPolicyVersion } from "@/lib/policies/backend";

/**
 * BFF endpoint for `PublishVersionButton`. Surfaces the backend's 409 verbatim — either
 * `NoDraftVersionToPublishError` (this version isn't a draft) or
 * `PolicyVersionConflictError` (a concurrent publish/draft-creation race on this policy;
 * the message itself tells the caller to retry).
 */
export async function POST(
  request: Request,
  { params }: { params: Promise<{ id: string; versionId: string }> },
): Promise<Response> {
  const accessToken = await readAccessToken();
  if (!accessToken) {
    return NextResponse.json({ detail: "Not authenticated." }, { status: 401 });
  }

  const { id, versionId } = await params;

  try {
    const version = await publishPolicyVersion(accessToken, id, versionId);
    return NextResponse.json(version);
  } catch (error) {
    if (error instanceof ApiError) {
      return NextResponse.json({ detail: error.detail }, { status: error.status });
    }
    return NextResponse.json({ detail: "Unexpected error." }, { status: 500 });
  }
}
