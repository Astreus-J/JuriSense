import type { Role } from "@/lib/auth/types";

export interface ApprovalPermissions {
  canRead: boolean;
  canUpdate: boolean;
}

/**
 * Default RBAC grid for the `approvals` module, mirrored from
 * `backend/app/identity/domain/rbac.py` (`DEFAULT_ROLE_GRID`): `admin`, `legal`,
 * `compliance`, `privacy`, `security`, `finance`, and `approver` get `read`+`update` — each
 * of the five specialist roles can itself be an `approver_role` target for its own policy
 * category, and `approver` is the generic Director/Approver persona that exists
 * specifically to resolve requests. `procurement`, `auditor`, and `viewer` are `read`-only:
 * they can see the inbox, but `ApprovalRequestRow` never renders Approve/Reject for them.
 *
 * (In practice, `GET /approvals/requests/pending` already only ever returns requests
 * routed to the caller's own role, so a read-only-role user shouldn't see any inbox items
 * to begin with under the default grid — this hint exists for the same defense-in-depth/
 * parity reason `lib/suppliers/permissions.ts`'s docstring gives: a per-user `ModulePermission`
 * override (ADR-012) could still change the picture this map doesn't know about.)
 *
 * Same caveat as every other permissions module here: this is a **UI-only hint**. The
 * backend's `require_permission(Module.APPROVALS, "update")` dependency remains the sole
 * source of truth — a 403 on approve/reject (e.g. a stale page after a role change) is
 * still a normal, handled error state, not a crash.
 */
const DEFAULT_APPROVAL_PERMISSIONS: Record<Role, ApprovalPermissions> = {
  admin: { canRead: true, canUpdate: true },
  procurement: { canRead: true, canUpdate: false },
  legal: { canRead: true, canUpdate: true },
  compliance: { canRead: true, canUpdate: true },
  privacy: { canRead: true, canUpdate: true },
  security: { canRead: true, canUpdate: true },
  finance: { canRead: true, canUpdate: true },
  approver: { canRead: true, canUpdate: true },
  auditor: { canRead: true, canUpdate: false },
  viewer: { canRead: true, canUpdate: false },
};

export function getApprovalPermissions(role: Role): ApprovalPermissions {
  return DEFAULT_APPROVAL_PERMISSIONS[role];
}
