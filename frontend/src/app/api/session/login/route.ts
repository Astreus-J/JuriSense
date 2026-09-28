import { NextResponse } from "next/server";

import { ApiError, login } from "@/lib/auth/backend";
import { setSessionCookies } from "@/lib/auth/cookies";

interface LoginBody {
  email?: unknown;
  password?: unknown;
}

/**
 * BFF login endpoint. The browser never sees the JWTs: this Route Handler
 * calls the Identity API server-side and relays the tokens into httpOnly
 * cookies (see `src/lib/auth/cookies.ts` for why).
 */
export async function POST(request: Request): Promise<Response> {
  const body = (await request.json().catch(() => null)) as LoginBody | null;
  if (typeof body?.email !== "string" || typeof body?.password !== "string") {
    return NextResponse.json({ detail: "Email and password are required." }, { status: 400 });
  }

  try {
    const tokens = await login(body.email, body.password);
    await setSessionCookies(tokens.access_token, tokens.refresh_token);
    return NextResponse.json({ ok: true });
  } catch (error) {
    if (error instanceof ApiError) {
      return NextResponse.json(
        { detail: error.detail, retryAfterSeconds: error.retryAfterSeconds },
        {
          status: error.status,
          headers:
            error.retryAfterSeconds !== undefined
              ? { "Retry-After": String(error.retryAfterSeconds) }
              : undefined,
        },
      );
    }
    return NextResponse.json({ detail: "Unexpected error." }, { status: 500 });
  }
}
