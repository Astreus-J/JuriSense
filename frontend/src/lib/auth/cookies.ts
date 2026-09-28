import "server-only";

import { cookies } from "next/headers";

import {
  ACCESS_TOKEN_COOKIE,
  ACCESS_TOKEN_MAX_AGE_SECONDS,
  cookieOptions,
  REFRESH_TOKEN_COOKIE,
  REFRESH_TOKEN_MAX_AGE_SECONDS,
} from "./cookie-config";

/**
 * Session cookies (STORY-1.2.1).
 *
 * The Identity API returns JWTs as a JSON body (`TokenResponse`), not as
 * `Set-Cookie` headers. Storing those tokens in `localStorage`/`sessionStorage`
 * and attaching them from client-side JavaScript would expose them to any
 * successful XSS on the page — exactly what the frontend-engineer persona's
 * "Secure token handling" standard and Next.js's own authentication guide
 * (`node_modules/next/dist/docs/01-app/02-guides/authentication.md`, "Stateless
 * Sessions") both warn against. Instead, the tokens are relayed once (in
 * `app/api/session/*` Route Handlers) into `httpOnly` cookies that
 * client-side JavaScript can never read, and every subsequent server-side
 * call (Server Components, Route Handlers, `proxy.ts`) reads them back from
 * the request via `cookies()`/`request.cookies`.
 */

export { ACCESS_TOKEN_COOKIE, REFRESH_TOKEN_COOKIE };

export async function readAccessToken(): Promise<string | undefined> {
  const store = await cookies();
  return store.get(ACCESS_TOKEN_COOKIE)?.value;
}

export async function readRefreshToken(): Promise<string | undefined> {
  const store = await cookies();
  return store.get(REFRESH_TOKEN_COOKIE)?.value;
}

/** Must only be called from a Route Handler or Server Function (see cookies() docs). */
export async function setSessionCookies(accessToken: string, refreshToken: string): Promise<void> {
  const store = await cookies();
  store.set(ACCESS_TOKEN_COOKIE, accessToken, cookieOptions(ACCESS_TOKEN_MAX_AGE_SECONDS));
  store.set(REFRESH_TOKEN_COOKIE, refreshToken, cookieOptions(REFRESH_TOKEN_MAX_AGE_SECONDS));
}

/** Must only be called from a Route Handler or Server Function (see cookies() docs). */
export async function clearSessionCookies(): Promise<void> {
  const store = await cookies();
  store.delete(ACCESS_TOKEN_COOKIE);
  store.delete(REFRESH_TOKEN_COOKIE);
}
