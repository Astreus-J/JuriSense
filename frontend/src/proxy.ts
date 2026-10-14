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
import { isCrossSiteMutation } from "@/lib/auth/csrf";
import { isJwtLikelyValid } from "@/lib/auth/jwt";
import { isSafeNextPath } from "@/lib/auth/safe-redirect";

/**
 * Proxy (Next.js 16 renamed Middleware to Proxy — see
 * `node_modules/next/dist/docs/01-app/01-getting-started/16-proxy.md`).
 *
 * Three jobs. The first two are both "optimistic" per Next's own authentication guide
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
 * 3. #129: reject a cross-site mutation against any `/api/*` BFF route handler (see
 *    `csrf.ts`'s own docstring for the full posture) -- done here, not inside each
 *    `route.ts`, so the check applies uniformly without needing to remember to add it
 *    to a 17th file later. `/api/*` is otherwise unrelated to jobs 1-2 (a Route
 *    Handler reads its own cookies and returns its own 401, never a page redirect), so
 *    it short-circuits before any of that logic runs.
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

  if (pathname.startsWith("/api/")) {
    if (isCrossSiteMutation(request)) {
      return NextResponse.json({ detail: "Cross-site request rejected." }, { status: 403 });
    }
    return NextResponse.next();
  }

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

  // #133: this optimistic `authenticated` check has no way to see a token the backend
  // revoked out of band (another tab's logout, an admin deactivation) -- its own `exp`
  // claim can still look "likely valid". Without this, that produces an infinite loop:
  // `requireSession()` finds the revoked token via the real `/auth/me` check, redirects
  // here to `/login?expired=1`, but THIS check still calls the same stale cookie
  // "authenticated" and bounces it straight back to the protected page, which bounces
  // it right back, forever.
  //
  // Code review (2026-10-14): an earlier version of this fix trusted the `expired=1`
  // query param as proof of real revocation and cleared cookies on that basis --
  // `expired` is attacker/visitor-controlled (a plain query string on a GET request,
  // not verified against the backend), so a crafted link could force-clear a victim's
  // genuinely valid session. Fixed without needing to trust the param at all: just
  // don't apply the "bounce an authenticated visitor off /login" redirect for this one
  // landing. The `/login` Server Component itself then runs its own REAL check
  // (`getSession()` -> `/auth/me`) and correctly decides whether to render the form or
  // redirect onward -- a verified result either way, with no loop possible (this skip
  // is a no-op read, not a mutation, so there's nothing here for a forged link to
  // trigger).
  const skipAuthOnlyRedirect =
    pathname === "/login" && request.nextUrl.searchParams.get("expired") === "1";

  let response: NextResponse;
  if (!authenticated && isProtected) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("next", pathname);
    response = NextResponse.redirect(loginUrl);
  } else if (authenticated && isAuthOnlyPage && !skipAuthOnlyRedirect) {
    // #132: `/login` itself redirects an already-authenticated visitor to its own
    // validated `next` target (`login/page.tsx`) -- but that code only runs if THIS
    // optimistic check ever lets the request through, which it normally doesn't (an
    // authenticated visitor hits this branch instead, previously always hardcoded to
    // `/dashboard`, silently dropping `next`). Mirrored here with the same shared
    // validator so the two can never disagree about what's safe.
    const next = pathname === "/login" ? request.nextUrl.searchParams.get("next") : null;
    const target = isSafeNextPath(next) ? next : "/dashboard";
    response = NextResponse.redirect(new URL(target, request.url));
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
  // #129: now also matches `/api/*` (previously excluded) so job 3's CSRF check runs
  // on every BFF route handler -- still excludes Next's own static/image assets.
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
