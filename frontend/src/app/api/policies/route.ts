import { NextResponse } from "next/server";

import { readAccessToken } from "@/lib/auth/cookies";
import { ApiError, createPolicy } from "@/lib/policies/backend";

interface CreatePolicyBody {
  name?: unknown;
}

/**
 * BFF endpoint for `CreatePolicyForm`. Mirrors `app/api/suppliers/route.ts`'s exact
 * request-validate / call-backend / unwrap-`ApiError` shape — the browser never holds the
 * access token (httpOnly cookie, see `src/lib/auth/cookies.ts`), so any mutation from a
 * Client Component goes through a Route Handler like this one.
 */
export async function POST(request: Request): Promise<Response> {
  const accessToken = await readAccessToken();
  if (!accessToken) {
    return NextResponse.json({ detail: "Not authenticated." }, { status: 401 });
  }

  const body = (await request.json().catch(() => null)) as CreatePolicyBody | null;
  if (typeof body?.name !== "string" || body.name.trim().length === 0) {
    return NextResponse.json({ detail: "A policy name is required." }, { status: 400 });
  }

  try {
    const created = await createPolicy(accessToken, body.name);
    return NextResponse.json(created, { status: 201 });
  } catch (error) {
    if (error instanceof ApiError) {
      return NextResponse.json({ detail: error.detail }, { status: error.status });
    }
    return NextResponse.json({ detail: "Unexpected error." }, { status: 500 });
  }
}
