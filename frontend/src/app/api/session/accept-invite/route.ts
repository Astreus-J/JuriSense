import { NextResponse } from "next/server";

import { acceptInvite, ApiError, login } from "@/lib/auth/backend";
import { setSessionCookies } from "@/lib/auth/cookies";

interface AcceptInviteBody {
  token?: unknown;
  password?: unknown;
  fullName?: unknown;
}

/**
 * Accepts an invitation and immediately logs the new user in, so they land
 * in the dashboard instead of being asked to retype the password they just
 * chose (persona: reduce friction / avoid re-asking for information the
 * system already has).
 */
export async function POST(request: Request): Promise<Response> {
  const body = (await request.json().catch(() => null)) as AcceptInviteBody | null;
  if (typeof body?.token !== "string" || typeof body?.password !== "string") {
    return NextResponse.json({ detail: "Token and password are required." }, { status: 400 });
  }
  const fullName = typeof body.fullName === "string" ? body.fullName : undefined;

  try {
    const user = await acceptInvite(body.token, body.password, fullName);
    const tokens = await login(user.email, body.password);
    await setSessionCookies(tokens.access_token, tokens.refresh_token);
    return NextResponse.json({ ok: true });
  } catch (error) {
    if (error instanceof ApiError) {
      return NextResponse.json({ detail: error.detail }, { status: error.status });
    }
    return NextResponse.json({ detail: "Unexpected error." }, { status: 500 });
  }
}
