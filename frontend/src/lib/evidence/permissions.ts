import type { Role } from "@/lib/auth/types";

export interface EvidencePermissions {
  canRead: boolean;
}

/**
 * Default RBAC grid for the `evidence` module, mirrored from
 * `backend/app/identity/domain/rbac.py` (`DEFAULT_ROLE_GRID`): every role gets `_READ` except
 * `procurement` (`_NONE`). Same caveat as `lib/compliance/permissions.ts`: this is a
 * **UI-only hint** for showing/hiding the Decision Passport entry point — the backend's
 * `require_permission(Module.EVIDENCE, "read")` dependency remains the sole source of
 * truth, and the fetch still handles a 403 as a normal error state.
 */
const DEFAULT_EVIDENCE_PERMISSIONS: Record<Role, EvidencePermissions> = {
  admin: { canRead: true },
  procurement: { canRead: false },
  legal: { canRead: true },
  compliance: { canRead: true },
  privacy: { canRead: true },
  security: { canRead: true },
  finance: { canRead: true },
  approver: { canRead: true },
  auditor: { canRead: true },
  viewer: { canRead: true },
};

export function getEvidencePermissions(role: Role): EvidencePermissions {
  return DEFAULT_EVIDENCE_PERMISSIONS[role];
}
