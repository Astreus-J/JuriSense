import { NextResponse } from "next/server";

import { logout as backendLogout } from "@/lib/auth/backend";
import { clearSessionCookies, readAccessToken, readRefreshToken } from "@/lib/auth/cookies";

/**
 * Best-effort logout: always clears the local cookies (so the user is signed
 * out client-side no matter what), and additionally asks the backend to
 * block the access token's `jti` and revoke the refresh token
 * (`app/identity/application/auth_service.logout`) so a copy of the token
 * can't be replayed after the user believes they've logged out.
 */
export async function POST(): Promise<Response> {
  const accessToken = await readAccessToken();
  const refreshToken = await readRefreshToken();

  if (accessToken) {
    try {
      await backendLogout(accessToken, refreshToken);
    } catch {
      // Backend logout failing (e.g. already-expired access token) must not
      // block the user from clearing their local session.
    }
  }

  await clearSessionCookies();
  return new NextResponse(null, { status: 204 });
}
