/**
 * Optimistic, unverified JWT expiry check.
 *
 * This intentionally does NOT verify the token's signature — that would
 * require sharing the backend's JWT secret with the frontend, which is not
 * how this system is designed (`backend/app/core/config.py` keeps
 * `jwt_secret_key` backend-only). This helper only answers "does this look
 * unexpired enough to skip a same-request refresh round-trip", used by
 * `proxy.ts` as an optimistic check per Next.js's own guidance
 * (`node_modules/next/dist/docs/01-app/02-guides/authentication.md`,
 * "Optimistic checks with Proxy"). The backend remains the sole source of
 * truth: every real request still carries the token as a Bearer header and
 * the API independently verifies and can reject it (e.g. after logout, via
 * its Redis token-block list).
 */
export function getJwtExpiryMs(token: string): number | null {
  const parts = token.split(".");
  if (parts.length !== 3) return null;
  try {
    const payloadJson = Buffer.from(parts[1], "base64url").toString("utf8");
    const payload = JSON.parse(payloadJson) as { exp?: number };
    if (typeof payload.exp !== "number") return null;
    return payload.exp * 1000;
  } catch {
    return null;
  }
}

/** A small buffer so a token that is *about* to expire is treated as expired. */
const EXPIRY_BUFFER_MS = 10_000;

export function isJwtLikelyValid(token: string | undefined): boolean {
  if (!token) return false;
  const expiryMs = getJwtExpiryMs(token);
  if (expiryMs === null) return false;
  return expiryMs - EXPIRY_BUFFER_MS > Date.now();
}
