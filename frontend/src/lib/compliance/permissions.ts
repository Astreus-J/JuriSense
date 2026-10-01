import type { Role } from "@/lib/auth/types";

export interface CompliancePermissions {
  canCreate: boolean;
  canRead: boolean;
}

/**
 * Default RBAC grid for the `compliance_reviews` module, mirrored from
 * `backend/app/identity/domain/rbac.py` (`DEFAULT_ROLE_GRID`): `admin`, `legal`, and
 * `compliance` get `create`+`read` (`_FULL`/`_CREATE_READ_UPDATE`); every other role is
 * `read`-only (`_READ`/`_READ_UPDATE` — `update` isn't modeled here, there's no update UI on
 * this screen).
 *
 * Unlike `lib/suppliers/permissions.ts`/`lib/contracts/permissions.ts`, `read` IS modeled
 * here (`canRead`) even though, same as those two modules, every one of the 10 default roles
 * already has it — `app/(app)/compliance/reviews/[id]/page.tsx` short-circuits on `!canRead`
 * before even attempting the fetch, per this story's brief. That branch is unreachable under
 * today's default grid; it exists for parity with that page's 403-handling structure, so a
 * narrower future per-user override (ADR-012) is respected without a code change here.
 *
 * Same caveat as the other two permissions files: this is a **UI-only hint** for
 * showing/hiding the "Run compliance review" entry point — the backend's `require_permission`
 * dependency (`Module.COMPLIANCE_REVIEWS`) remains the sole source of truth, and every
 * mutating call still goes to the real API and handles a 403 as a normal error state.
 */
const DEFAULT_COMPLIANCE_PERMISSIONS: Record<Role, CompliancePermissions> = {
  admin: { canCreate: true, canRead: true },
  procurement: { canCreate: false, canRead: true },
  legal: { canCreate: true, canRead: true },
  compliance: { canCreate: true, canRead: true },
  privacy: { canCreate: false, canRead: true },
  security: { canCreate: false, canRead: true },
  finance: { canCreate: false, canRead: true },
  approver: { canCreate: false, canRead: true },
  auditor: { canCreate: false, canRead: true },
  viewer: { canCreate: false, canRead: true },
};

export function getCompliancePermissions(role: Role): CompliancePermissions {
  return DEFAULT_COMPLIANCE_PERMISSIONS[role];
}
