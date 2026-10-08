import "server-only";

import { ApiError, request } from "@/lib/auth/backend";
import { isRole } from "@/lib/auth/types";
import type { Role } from "@/lib/auth/types";
import type {
  Invitation,
  InvitationStatus,
  Organization,
  Plan,
  TeamMember,
  UserStatus,
} from "./types";

export { ApiError };

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/**
 * Mirrors `assertValidSupplierId` in `src/lib/suppliers/backend.ts` exactly, including the
 * confused-deputy risk that function's doc comment explains in full: a dynamic route segment
 * (`[id]`) can carry a decoded `../` sequence into a template-string URL. Every backend user
 * id is a UUID, so reject anything else before it is ever interpolated into a backend path.
 */
function assertValidUserId(userId: string): void {
  if (!UUID_PATTERN.test(userId)) {
    throw new ApiError(400, "Invalid user id.");
  }
}

/**
 * Thin server-only client for the Identity API's organization/user-management endpoints
 * (`backend/app/identity/api/organizations.py`, `users.py`), following the exact pattern of
 * `src/lib/suppliers/backend.ts`: reuse `request()` from `src/lib/auth/backend.ts` (base URL
 * resolution, Bearer token, no-store caching, `ApiError` unwrapping) rather than a second
 * HTTP client. Never imported by a Client Component — `server-only` turns an accidental
 * client import into a build error; mutations from Client Components go through the
 * `/api/users/*` Route Handlers instead.
 */

interface RawOrganizationResponse {
  id: string;
  name: string;
  plan: string;
  user_limit: number | null;
  supplier_limit: number | null;
  storage_limit_gb: number | null;
  ai_execution_limit: number | null;
  active_user_count: number;
  created_at: string;
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

interface RawInvitationResponse {
  id: string;
  email: string;
  full_name: string | null;
  role: string;
  status: string;
  expires_at: string;
  created_at: string;
}

function toOrganization(raw: RawOrganizationResponse): Organization {
  return {
    id: raw.id,
    name: raw.name,
    plan: raw.plan as Plan,
    userLimit: raw.user_limit,
    supplierLimit: raw.supplier_limit,
    storageLimitGb: raw.storage_limit_gb,
    aiExecutionLimit: raw.ai_execution_limit,
    activeUserCount: raw.active_user_count,
    createdAt: raw.created_at,
  };
}

/**
 * Falls back to "viewer" for an unrecognized role string — the same fail-safe
 * `toSessionUser` (`src/lib/auth/backend.ts`) applies, found in that file's own security
 * review: an unrecognized role must never crash this screen.
 */
function toRole(raw: string): Role {
  return isRole(raw) ? raw : "viewer";
}

function toTeamMember(raw: RawUserResponse): TeamMember {
  return {
    id: raw.id,
    organizationId: raw.organization_id,
    fullName: raw.full_name,
    email: raw.email,
    phone: raw.phone,
    role: toRole(raw.role),
    status: raw.status as UserStatus,
    isActive: raw.is_active,
    lastLoginAt: raw.last_login_at,
    createdAt: raw.created_at,
  };
}

function toInvitation(raw: RawInvitationResponse): Invitation {
  return {
    id: raw.id,
    email: raw.email,
    fullName: raw.full_name,
    role: toRole(raw.role),
    status: raw.status as InvitationStatus,
    expiresAt: raw.expires_at,
    createdAt: raw.created_at,
  };
}

/** Gated server-side on the real `organization_settings` read permission (`admin`, `security`,
 * and `auditor` by default — see `getOrganizationPermissions`), not hardcoded admin-only. */
export async function getMyOrganization(accessToken: string): Promise<Organization> {
  const raw = await request<RawOrganizationResponse>("/organizations/me", { accessToken });
  return toOrganization(raw);
}

/** Admin-only server-side (`CurrentAdmin`), regardless of the general RBAC grid. */
export async function listUsers(accessToken: string): Promise<TeamMember[]> {
  const raw = await request<RawUserResponse[]>("/users", { accessToken });
  return raw.map(toTeamMember);
}

export interface CreateUserInput {
  fullName: string;
  email: string;
  password: string;
  role: Role;
  phone?: string;
}

export async function createUser(
  accessToken: string,
  input: CreateUserInput,
): Promise<TeamMember> {
  const raw = await request<RawUserResponse>("/users", {
    method: "POST",
    accessToken,
    body: JSON.stringify({
      full_name: input.fullName,
      email: input.email,
      password: input.password,
      role: input.role,
      phone: input.phone ?? null,
    }),
  });
  return toTeamMember(raw);
}

export interface UpdateUserInput {
  fullName?: string;
  phone?: string;
  role?: Role;
  status?: UserStatus;
}

/** Partial update — only the fields present on `input` are sent (the backend's
 * `UpdateUserRequest` is `extra="forbid"`, so this must never send unset fields). */
export async function updateUser(
  accessToken: string,
  userId: string,
  input: UpdateUserInput,
): Promise<TeamMember> {
  assertValidUserId(userId);
  const body: Record<string, unknown> = {};
  if (input.fullName !== undefined) body.full_name = input.fullName;
  if (input.phone !== undefined) body.phone = input.phone;
  if (input.role !== undefined) body.role = input.role;
  if (input.status !== undefined) body.status = input.status;

  const raw = await request<RawUserResponse>(`/users/${userId}`, {
    method: "PATCH",
    accessToken,
    body: JSON.stringify(body),
  });
  return toTeamMember(raw);
}

/** Logical deactivation, not a hard delete — see `user_service.deactivate_user`. */
export async function deactivateUser(accessToken: string, userId: string): Promise<void> {
  assertValidUserId(userId);
  await request<void>(`/users/${userId}`, { method: "DELETE", accessToken });
}

/** Admin-only server-side (`CurrentAdmin`), regardless of the general RBAC grid. */
export async function listInvites(accessToken: string): Promise<Invitation[]> {
  const raw = await request<RawInvitationResponse[]>("/users/invites", { accessToken });
  return raw.map(toInvitation);
}

export interface CreateInviteInput {
  email: string;
  role: Role;
  fullName?: string;
}

/** Resending to the same email cancels the previous pending invitation
 * (`invite_service.invite_user`) — not an error on the second call. */
export async function createInvite(
  accessToken: string,
  input: CreateInviteInput,
): Promise<Invitation> {
  const raw = await request<RawInvitationResponse>("/users/invites", {
    method: "POST",
    accessToken,
    body: JSON.stringify({
      email: input.email,
      role: input.role,
      full_name: input.fullName ?? null,
    }),
  });
  return toInvitation(raw);
}
