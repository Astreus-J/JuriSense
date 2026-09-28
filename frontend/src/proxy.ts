import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { ApiError, refreshTokens } from "@/lib/auth/backend";
import {
  ACCESS_TOKEN_COOKIE,
  ACCESS_TOKEN_MAX_AGE_SECONDS,
  cookieOptions,
  REFRESH_TOKEN_COOKIE,
  REFRESH_TOKEN_MAX_AGE_SECONDS,
} from "@/lib/auth/cookie-config";
import { isJwtLikelyValid } from "@/lib/auth/jwt";

/**
 * Proxy (Next.js 16 renamed Middleware to Proxy — see
 * `node_modules/next/dist/docs/01-app/01-getting-started/16-proxy.md`).
 *
 * Two jobs, both "optimistic" per Next's own authentication guide
 * (`node_modules/next/dist/docs/01-app/02-guides/authentication.md`,
 * "Optimistic checks with Proxy"): the real authorization check always
 * happens server-side against `/auth/me` (`src/lib/auth/session.ts`).
 *
 * 1. Silent token refresh: if the access token cookie is missing/expired but
 *    a refresh token cookie is present, refresh here — this is the only
 *    place in the app allowed to rewrite cookies before a Server Component
 *    renders (`cookies().set()` cannot be called during RSC rendering; see
 *    `src/lib/auth/session.ts`'s comment).
 * 2. Redirect unauthenticated users away from the authenticated app, and
 *    authenticated users away from the login/invite-accept screens.
 */
const PROTECTED_PREFIXES = [
  "/dashboard",
  "/suppliers",
  "/contracts",
  "/policies",
  "/approvals",
  "/evidence",
  "/integrations",
  "/settings",
];

const AUTH_ONLY_PAGES = ["/login", "/invite/accept"];

function matchesPrefix(pathname: string, prefixes: string[]): boolean {
  return prefixes.some((prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`));
}

export async function proxy(request: NextRequest): Promise<NextResponse> {
  const { pathname } = request.nextUrl;

  let accessToken = request.cookies.get(ACCESS_TOKEN_COOKIE)?.value;
  const refreshToken = request.cookies.get(REFRESH_TOKEN_COOKIE)?.value;

  let cookieUpdate: { access: string; refresh: string } | "clear" | null = null;

  if (!isJwtLikelyValid(accessToken) && refreshToken) {
    try {
      const refreshed = await refreshTokens(refreshToken);
      accessToken = refreshed.access_token;
      cookieUpdate = { access: refreshed.access_token, refresh: refreshed.refresh_token };
    } catch (error) {
      accessToken = undefined;
      // Only clear cookies on an actual rejection, not a transient network
      // error reaching the backend — a network blip shouldn't log everyone
      // out.
      if (error instanceof ApiError) cookieUpdate = "clear";
    }
  }

  const authenticated = isJwtLikelyValid(accessToken);
  const isProtected = matchesPrefix(pathname, PROTECTED_PREFIXES);
  const isAuthOnlyPage = matchesPrefix(pathname, AUTH_ONLY_PAGES);

  let response: NextResponse;
  if (!authenticated && isProtected) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("next", pathname);
    response = NextResponse.redirect(loginUrl);
  } else if (authenticated && isAuthOnlyPage) {
    response = NextResponse.redirect(new URL("/dashboard", request.url));
  } else {
    response = NextResponse.next();
  }

  if (cookieUpdate === "clear") {
    response.cookies.delete(ACCESS_TOKEN_COOKIE);
    response.cookies.delete(REFRESH_TOKEN_COOKIE);
  } else if (cookieUpdate) {
    response.cookies.set(ACCESS_TOKEN_COOKIE, cookieUpdate.access, cookieOptions(ACCESS_TOKEN_MAX_AGE_SECONDS));
    response.cookies.set(
      REFRESH_TOKEN_COOKIE,
      cookieUpdate.refresh,
      cookieOptions(REFRESH_TOKEN_MAX_AGE_SECONDS),
    );
  }

  return response;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|api/).*)"],
};
