import type { Role } from "@/lib/auth/types";

export interface ContractPermissions {
  canCreate: boolean;
  canUpdate: boolean;
}

/**
 * Default RBAC grid for the `contracts` module, mirrored from
 * `backend/app/identity/domain/rbac.py` (`DEFAULT_ROLE_GRID`): `admin`, `procurement`, and
 * `legal` get `create`/`update` by default (`_FULL`/`_CREATE_READ_UPDATE`), every other
 * role is read-only (`_READ`).
 *
 * Same caveat as `lib/suppliers/permissions.ts`: this is a **UI-only hint** for
 * showing/hiding actions (the "Upload contract" entry point, the confirmation form) — an
 * org admin can still grant a per-user `ModulePermission` override this map doesn't know
 * about, so every mutating call still goes to the real API and handles a 403 as a normal
 * error state. The backend's `require_permission` dependency remains the sole source of
 * truth.
 *
 * `canUpdate` gates who can submit `POST .../confirm` (CON-005) from the detail screen —
 * `legal`, unlike in Suppliers, does get it here, matching `Module.CONTRACTS`'s grid
 * exactly (Legal owns contract review, not just Compliance/Procurement).
 */
const DEFAULT_CONTRACT_PERMISSIONS: Record<Role, ContractPermissions> = {
  admin: { canCreate: true, canUpdate: true },
  procurement: { canCreate: true, canUpdate: true },
  legal: { canCreate: true, canUpdate: true },
  compliance: { canCreate: false, canUpdate: false },
  privacy: { canCreate: false, canUpdate: false },
  security: { canCreate: false, canUpdate: false },
  finance: { canCreate: false, canUpdate: false },
  approver: { canCreate: false, canUpdate: false },
  auditor: { canCreate: false, canUpdate: false },
  viewer: { canCreate: false, canUpdate: false },
};

export function getContractPermissions(role: Role): ContractPermissions {
  return DEFAULT_CONTRACT_PERMISSIONS[role];
}
