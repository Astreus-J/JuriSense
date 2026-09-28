import "server-only";

import { cache } from "react";
import { redirect } from "next/navigation";

import { ApiError, fetchCurrentUser } from "./backend";
import { readAccessToken } from "./cookies";
import type { SessionUser } from "./types";

/**
 * Data Access Layer for the current session (Next.js's recommended pattern —
 * see `node_modules/next/dist/docs/01-app/02-guides/authentication.md`,
 * "Creating a Data Access Layer"). `cache()` de-dupes repeated calls within a
 * single render pass (e.g. the `(app)` layout and its page both calling
 * `requireSession()`), so we only ever hit `/auth/me` once per request.
 *
 * By design this function never *writes* a cookie: Next.js does not allow
 * `cookies().set()` during Server Component rendering (only in Route
 * Handlers/Server Functions). Silent token refresh instead happens in
 * `src/proxy.ts`, which runs before rendering and is allowed to rewrite
 * response cookies. If we still get a 401 here, the access token proxy
 * refreshed was rejected by the backend for some other reason (e.g. it was
 * revoked via logout in another tab) — treat that as a real expiry.
 */
export const getSession = cache(async (): Promise<SessionUser | null> => {
  const accessToken = await readAccessToken();
  if (!accessToken) return null;

  try {
    return await fetchCurrentUser(accessToken);
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) return null;
    throw error;
  }
});

/** For Server Components that require an authenticated session (e.g. the app shell layout). */
export async function requireSession(): Promise<SessionUser> {
  const session = await getSession();
  if (!session) redirect("/login?expired=1");
  return session;
}
