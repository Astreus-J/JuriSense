/**
 * Identity types mirrored from the backend (source of truth:
 * backend/app/identity/domain/constants.py and backend/app/identity/api/schemas.py).
 *
 * Do not add fields here that the API does not actually return — see
 * `docs/09-planning/backlog.md` STORY-1.2.1 and `UserResponse` in
 * `backend/app/identity/api/schemas.py`.
 */

/** The 10 compliance roles defined in ADR-003. Exact string values from the API. */
export const ROLES = [
  "admin",
  "procurement",
  "legal",
  "compliance",
  "privacy",
  "security",
  "finance",
  "approver",
  "auditor",
  "viewer",
] as const;

export type Role = (typeof ROLES)[number];

export function isRole(value: string): value is Role {
  return (ROLES as readonly string[]).includes(value);
}

/** All 10 role values are single lowercase words — capitalize for display. */
export function formatRoleLabel(role: Role): string {
  return role.charAt(0).toUpperCase() + role.slice(1);
}

/**
 * A single organization membership for the current user.
 *
 * `GET /api/auth/me` today returns exactly one organization per user (a flat
 * `organization_id` + `role` on `UserResponse`), even though the domain model
 * (`docs/03-domain/domain-model.md`, `Membership`) already allows a user to
 * belong to more than one organization. `organizationName` is `null` because
 * the API does not return an organization name anywhere reachable from the
 * authenticated session yet — the UI must degrade gracefully until a future
 * API change adds it (see the frontend README-equivalent note in
 * `src/components/app-shell/OrgSwitcher.tsx`).
 */
export interface Membership {
  organizationId: string;
  organizationName: string | null;
  role: Role;
}

/** The authenticated user, shaped for what the app shell actually needs. */
export interface SessionUser {
  id: string;
  fullName: string;
  email: string;
  role: Role;
  status: string;
  isActive: boolean;
  organizationId: string;
  /** Always at least one entry — see `Membership` above. */
  memberships: Membership[];
}
