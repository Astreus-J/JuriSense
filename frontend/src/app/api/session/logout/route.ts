import { NextResponse } from "next/server";

import { logout as backendLogout, refreshTokens } from "@/lib/auth/backend";
import { clearSessionCookies, readAccessToken, readRefreshToken } from "@/lib/auth/cookies";

/**
 * Best-effort logout: always clears the local cookies (so the user is signed
 * out client-side no matter what), and additionally asks the backend to
 * block the access token's `jti` and revoke the refresh token
 * (`app/identity/application/auth_service.logout`) so a copy of the token
 * can't be replayed after the user believes they've logged out.
 *
 * `/auth/logout` requires a currently-valid access token (it identifies the
 * caller and blocks that specific jti) -- but the access-token cookie has a
 * short (15min) lifetime and routinely expires before the 7-day refresh
 * token does, e.g. an idle tab. Found in security review: the original
 * version only attempted backend logout `if (accessToken)`, silently
 * skipping refresh-token revocation whenever that cookie was already gone --
 * "logout" cleared the local session but left a still-valid refresh token
 * that could be replayed if it had leaked. If only a refresh token remains,
 * spend it on one refresh call to mint a fresh access token specifically so
 * logout can revoke both.
 */
export async function POST(): Promise<Response> {
  let accessToken = await readAccessToken();
  const refreshToken = await readRefreshToken();

  if (!accessToken && refreshToken) {
    try {
      accessToken = (await refreshTokens(refreshToken)).access_token;
    } catch {
      // Refresh token is itself invalid/expired -- nothing left to revoke.
    }
  }

  if (accessToken) {
    try {
      await backendLogout(accessToken, refreshToken);
    } catch {
      // Backend logout failing must not block clearing the local session.
    }
  }

  await clearSessionCookies();
  return new NextResponse(null, { status: 204 });
}
