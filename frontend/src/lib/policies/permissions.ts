import type { Role } from "@/lib/auth/types";

export interface PolicyPermissions {
  canCreate: boolean;
  canUpdate: boolean;
}

/**
 * Default RBAC grid for the `policies` module, mirrored from
 * `backend/app/identity/domain/rbac.py` (`DEFAULT_ROLE_GRID`): `admin` plus the five
 * policy-authoring roles (`legal`, `compliance`, `privacy`, `security`, `finance`) get
 * `create`/`update`; `procurement`, `approver`, `auditor`, and `viewer` are read-only.
 *
 * Same caveat as `lib/suppliers/permissions.ts` and `lib/contracts/permissions.ts`: this
 * is a **UI-only hint** for showing/hiding actions (the "Create policy" entry point, "New
 * draft version", "Add rule"/"Edit rule", "Publish") — an org admin can still grant a
 * per-user `ModulePermission` override this map doesn't know about, so every mutating
 * call still goes to the real API and handles a 403 as a normal error state. The
 * backend's `require_permission` dependency remains the sole source of truth.
 *
 * `canCreate` gates creating a policy, a draft version, and a rule
 * (`CanCreatePolicies` in `backend/app/policies/api/routes.py`); `canUpdate` gates editing
 * a rule and publishing a version (`CanUpdatePolicies`) — both map to the same
 * `Module.POLICIES` grid entry, so one permissions object covers every mutating action on
 * this screen.
 */
const DEFAULT_POLICY_PERMISSIONS: Record<Role, PolicyPermissions> = {
  admin: { canCreate: true, canUpdate: true },
  procurement: { canCreate: false, canUpdate: false },
  legal: { canCreate: true, canUpdate: true },
  compliance: { canCreate: true, canUpdate: true },
  privacy: { canCreate: true, canUpdate: true },
  security: { canCreate: true, canUpdate: true },
  finance: { canCreate: true, canUpdate: true },
  approver: { canCreate: false, canUpdate: false },
  auditor: { canCreate: false, canUpdate: false },
  viewer: { canCreate: false, canUpdate: false },
};

export function getPolicyPermissions(role: Role): PolicyPermissions {
  return DEFAULT_POLICY_PERMISSIONS[role];
}
