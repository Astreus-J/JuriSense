/**
 * Organization/Team types mirrored from the backend (source of truth:
 * `backend/app/identity/api/schemas.py` and `backend/app/identity/domain/constants.py`).
 *
 * Field names are camelCase on this side of the boundary; `src/lib/organization/backend.ts`
 * is the only place that maps the API's snake_case shape into these types.
 */

import type { Role } from "@/lib/auth/types";

/** `Plan` per `backend/app/identity/domain/constants.py`. */
export const PLANS = ["starter", "business", "growth", "enterprise"] as const;
export type Plan = (typeof PLANS)[number];

export const PLAN_LABELS: Record<Plan, string> = {
  starter: "Starter",
  business: "Business",
  growth: "Growth",
  enterprise: "Enterprise",
};

/** `UserStatus` per `backend/app/identity/domain/constants.py`. */
export const USER_STATUSES = ["active", "inactive", "blocked", "pending"] as const;
export type UserStatus = (typeof USER_STATUSES)[number];

export const USER_STATUS_LABELS: Record<UserStatus, string> = {
  active: "Active",
  inactive: "Inactive",
  blocked: "Blocked",
  pending: "Pending",
};

/** `InvitationStatus` per `backend/app/identity/domain/constants.py`. */
export const INVITATION_STATUSES = ["pending", "accepted", "expired", "cancelled"] as const;
export type InvitationStatus = (typeof INVITATION_STATUSES)[number];

export const INVITATION_STATUS_LABELS: Record<InvitationStatus, string> = {
  pending: "Pending",
  accepted: "Accepted",
  expired: "Expired",
  cancelled: "Cancelled",
};

/**
 * The `/settings/organization` screen's plan/usage panel (`OrganizationResponse`). The four
 * `*Limit` fields are `null` on the Enterprise plan — a negotiated, unlimited capacity, not
 * a numeric cap — render that as "Unlimited", never a blank or zero value (see
 * `OrganizationPlanPanel`).
 */
export interface Organization {
  id: string;
  name: string;
  plan: Plan;
  userLimit: number | null;
  supplierLimit: number | null;
  storageLimitGb: number | null;
  aiExecutionLimit: number | null;
  activeUserCount: number;
  createdAt: string;
}

/**
 * A member of the organization's team (`UserResponse`). Named `TeamMember`, not `User`, to
 * avoid colliding with the DOM's global `User` type and to read naturally on this screen
 * ("the team").
 */
export interface TeamMember {
  id: string;
  organizationId: string;
  fullName: string;
  email: string;
  phone: string | null;
  role: Role;
  status: UserStatus;
  isActive: boolean;
  lastLoginAt: string | null;
  createdAt: string;
}

/** A pending (or past) invitation (`InvitationResponse`). */
export interface Invitation {
  id: string;
  email: string;
  fullName: string | null;
  role: Role;
  status: InvitationStatus;
  expiresAt: string;
  createdAt: string;
}
