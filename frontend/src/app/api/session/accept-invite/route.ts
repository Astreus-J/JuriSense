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
 *
 * #131: these are two sequential backend calls, and the invite token is single-use --
 * once `acceptInvite` succeeds, it's gone. The original version wrapped both calls in
 * one `try`, so a failure in the *second* call (e.g. a transient network blip, or the
 * login endpoint's own rate limit) was indistinguishable from the first one failing:
 * the frontend got a generic error implying nothing happened, while the account had
 * actually already been created and the token burned -- the user had no way to retry
 * (the token is gone) and no session either. Split into two steps: a login failure
 * after a successful accept now reports `requiresManualLogin` instead of an error, so
 * the frontend can send the user to a normal login instead of a dead end.
 */
export async function POST(request: Request): Promise<Response> {
  const body = (await request.json().catch(() => null)) as AcceptInviteBody | null;
  if (typeof body?.token !== "string" || typeof body?.password !== "string") {
    return NextResponse.json({ detail: "Token and password are required." }, { status: 400 });
  }
  const fullName = typeof body.fullName === "string" ? body.fullName : undefined;

  let email: string;
  try {
    const user = await acceptInvite(body.token, body.password, fullName);
    email = user.email;
  } catch (error) {
    if (error instanceof ApiError) {
      return NextResponse.json({ detail: error.detail }, { status: error.status });
    }
    return NextResponse.json({ detail: "Unexpected error." }, { status: 500 });
  }

  try {
    const tokens = await login(email, body.password);
    await setSessionCookies(tokens.access_token, tokens.refresh_token);
    return NextResponse.json({ ok: true });
  } catch {
    // The account already exists with the password just submitted -- never report
    // this as a failure of the whole operation.
    return NextResponse.json({ ok: true, requiresManualLogin: true, email });
  }
}
