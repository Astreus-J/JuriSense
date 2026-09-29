import type { Role } from "@/lib/auth/types";

export interface SupplierPermissions {
  canCreate: boolean;
  canUpdate: boolean;
}

/**
 * Default RBAC grid for the `suppliers` module, mirrored from
 * `backend/app/identity/domain/rbac.py` (`DEFAULT_ROLE_GRID`): only `admin` and
 * `procurement` get `create`/`update` by default, everyone else is read-only.
 *
 * This is a **UI-only hint** for showing/hiding actions (the "Register supplier" button,
 * the re-check/status-change controls) before a request even round-trips. An org admin can
 * still grant a specific user a per-user `ModulePermission` override (ADR-012) this map does
 * not know about, so it is deliberately not used to block navigation or to skip error
 * handling — every mutating call still goes to the real API and handles a 403 as a normal
 * error state. The backend's `require_permission` dependency remains the sole source of
 * truth (persona: "Backend authorization remains authoritative. Never assume hidden UI
 * equals authorization.").
 *
 * `read` is intentionally not modeled here: every role has at least read access in the
 * default grid, so the list/detail screens always attempt the fetch and surface a real 403
 * from the API (which *can* happen under a per-user override) rather than precomputing a
 * hint that would just be `true` for all ten roles.
 */
const DEFAULT_SUPPLIER_PERMISSIONS: Record<Role, SupplierPermissions> = {
  admin: { canCreate: true, canUpdate: true },
  procurement: { canCreate: true, canUpdate: true },
  legal: { canCreate: false, canUpdate: false },
  compliance: { canCreate: false, canUpdate: false },
  privacy: { canCreate: false, canUpdate: false },
  security: { canCreate: false, canUpdate: false },
  finance: { canCreate: false, canUpdate: false },
  approver: { canCreate: false, canUpdate: false },
  auditor: { canCreate: false, canUpdate: false },
  viewer: { canCreate: false, canUpdate: false },
};

export function getSupplierPermissions(role: Role): SupplierPermissions {
  return DEFAULT_SUPPLIER_PERMISSIONS[role];
}
