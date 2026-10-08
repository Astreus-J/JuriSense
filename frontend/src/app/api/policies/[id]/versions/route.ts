import { NextResponse } from "next/server";

import { readAccessToken } from "@/lib/auth/cookies";
import { ApiError, createDraftVersion } from "@/lib/policies/backend";

/**
 * BFF endpoint for `CreateDraftVersionButton` (BR-POL-001's copy-modify path). No request
 * body — the backend derives everything it needs (the policy id, the current version to
 * copy rules from) from the URL and the caller's session.
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

  try {
    const version = await createDraftVersion(accessToken, id);
    return NextResponse.json(version, { status: 201 });
  } catch (error) {
    if (error instanceof ApiError) {
      return NextResponse.json({ detail: error.detail }, { status: error.status });
    }
    return NextResponse.json({ detail: "Unexpected error." }, { status: 500 });
  }
}
