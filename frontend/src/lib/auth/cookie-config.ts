/**
 * Cookie names/options shared between `src/lib/auth/cookies.ts` (used from
 * Server Components/Route Handlers, via `next/headers`) and `src/proxy.ts`
 * (used from Proxy, via `NextResponse.cookies` — a different API with the
 * same option shape). Kept dependency-free so both can import it.
 */

export const ACCESS_TOKEN_COOKIE = "jurisense_access_token";
export const REFRESH_TOKEN_COOKIE = "jurisense_refresh_token";

// Mirrors backend/app/core/config.py defaults (access_token_expire_minutes=15,
// refresh_token_expire_days=7). If an operator changes those settings, the
// cookie simply expires a little earlier/later than the JWT itself, which is
// harmless — the backend is always the source of truth on token validity.
export const ACCESS_TOKEN_MAX_AGE_SECONDS = 15 * 60;
export const REFRESH_TOKEN_MAX_AGE_SECONDS = 7 * 24 * 60 * 60;

const isProduction = process.env.NODE_ENV === "production";

export function cookieOptions(maxAgeSeconds: number) {
  return {
    httpOnly: true,
    secure: isProduction,
    sameSite: "lax" as const,
    path: "/",
    maxAge: maxAgeSeconds,
  };
}
