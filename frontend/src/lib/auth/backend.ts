import "server-only";

import { isRole, type Role, type SessionUser } from "./types";

/**
 * Thin server-only client for the Identity API (backend/app/identity/api/routes.py
 * and users.py). Never imported by a Client Component — the `server-only` import
 * above turns any accidental client import into a build error.
 *
 * Base URL resolution:
 * - `API_URL`: server-side-only override, meant for when the Next.js server
 *   itself runs inside a container and must reach the backend by its Docker
 *   Compose service name (e.g. `http://backend:8000/api`) rather than
 *   `localhost`.
 * - `NEXT_PUBLIC_API_URL`: the browser-facing URL already defined in
 *   `docker-compose.yml`; also a perfectly valid server-side default when the
 *   Next.js dev server runs directly on the host (`npm run dev`), because in
 *   that case `localhost:8000` is reachable from both the browser and the
 *   Next.js process.
 */
const API_BASE_URL =
  process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

export class ApiError extends Error {
  readonly status: number;
  readonly detail: string;
  readonly retryAfterSeconds?: number;

  constructor(status: number, detail: string, retryAfterSeconds?: number) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
    this.retryAfterSeconds = retryAfterSeconds;
  }
}

async function parseErrorDetail(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string") return body.detail;
  } catch {
    // Non-JSON error body — fall through to a generic message.
  }
  return "Unexpected error communicating with the server.";
}

/**
 * The one low-level fetch helper every server-only backend client in this app
 * should go through (exported so `src/lib/suppliers/backend.ts` and future
 * bounded-context clients reuse the same base-URL resolution, Bearer-token
 * attachment, no-store caching, and `ApiError` unwrapping instead of hand
 * -rolling a second HTTP client with different error handling).
 */
export async function request<T>(
  path: string,
  init: RequestInit & { accessToken?: string } = {},
): Promise<T> {
  const { accessToken, headers, ...rest } = init;
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...rest,
    headers: {
      "Content-Type": "application/json",
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      ...headers,
    },
    // Every call here is user- or request-specific; never let Next.js cache it.
    cache: "no-store",
  });

  if (!response.ok) {
    const detail = await parseErrorDetail(response);
    const retryAfterHeader = response.headers.get("Retry-After");
    throw new ApiError(
      response.status,
      detail,
      retryAfterHeader ? Number(retryAfterHeader) : undefined,
    );
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

/**
 * `request()`'s multipart counterpart — needed because `request()` unconditionally sets
 * `Content-Type: application/json`, which is wrong for a `FormData` body (the browser/
 * runtime must set its own `multipart/form-data; boundary=...` header, which is only
 * possible when the caller does *not* set `Content-Type` at all). Everything else
 * (base-URL resolution, Bearer token, no-store caching, `ApiError` unwrapping) matches
 * `request()` exactly — `lib/contracts/backend.ts`'s contract upload is the first caller
 * (`POST /contracts/upload` takes `multipart/form-data`, unlike every other endpoint in
 * this codebase so far).
 */
export async function requestMultipart<T>(
  path: string,
  init: { accessToken?: string; formData: FormData; method?: string },
): Promise<T> {
  const { accessToken, formData, method = "POST" } = init;
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : undefined,
    body: formData,
    cache: "no-store",
  });

  if (!response.ok) {
    const detail = await parseErrorDetail(response);
    const retryAfterHeader = response.headers.get("Retry-After");
    throw new ApiError(
      response.status,
      detail,
      retryAfterHeader ? Number(retryAfterHeader) : undefined,
    );
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

interface RawUserResponse {
  id: string;
  organization_id: string;
  full_name: string;
  email: string;
  phone: string | null;
  role: string;
  status: string;
  is_active: boolean;
  last_login_at: string | null;
  created_at: string;
}

function toSessionUser(raw: RawUserResponse): SessionUser {
  // Found in security review: an unvalidated `as Role` cast let any
  // unrecognized role string from the backend (a future role added
  // backend-first, or a data inconsistency) flow straight into
  // `getNavItemsForRole`, whose `ROLE_NAV_ITEMS[role]` lookup would then be
  // `undefined` and crash the whole authenticated shell for that user. Fail
  // safe instead: fall back to the least-privileged role rather than the
  // unrecognized value.
  const role: Role = isRole(raw.role) ? raw.role : "viewer";
  return {
    id: raw.id,
    fullName: raw.full_name,
    email: raw.email,
    role,
    status: raw.status,
    isActive: raw.is_active,
    organizationId: raw.organization_id,
    // The API returns one organization per user today; wrapped in a list so
    // the UI (OrgSwitcher) already handles the multi-membership case the
    // domain model allows (`docs/03-domain/domain-model.md`, `Membership`).
    memberships: [{ organizationId: raw.organization_id, organizationName: null, role }],
  };
}

export async function login(email: string, password: string): Promise<TokenPair> {
  return request<TokenPair>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function fetchCurrentUser(accessToken: string): Promise<SessionUser> {
  const raw = await request<RawUserResponse>("/auth/me", { accessToken });
  return toSessionUser(raw);
}

export async function refreshTokens(refreshToken: string): Promise<TokenPair> {
  return request<TokenPair>("/auth/refresh", {
    method: "POST",
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
}

export async function logout(accessToken: string, refreshToken?: string): Promise<void> {
  await request<void>("/auth/logout", {
    method: "POST",
    accessToken,
    body: JSON.stringify({ refresh_token: refreshToken ?? null }),
  });
}

export async function acceptInvite(
  token: string,
  password: string,
  fullName?: string,
): Promise<SessionUser> {
  const raw = await request<RawUserResponse>("/users/accept-invite", {
    method: "POST",
    body: JSON.stringify({ token, password, full_name: fullName ?? null }),
  });
  return toSessionUser(raw);
}
