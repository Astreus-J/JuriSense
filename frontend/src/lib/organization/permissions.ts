import type { Role } from "@/lib/auth/types";

export interface OrganizationPermissions {
  /**
   * Can view the plan/usage panel at all. Mirrors the real `organization_settings` row of
   * `DEFAULT_ROLE_GRID` in `backend/app/identity/domain/rbac.py` — `admin`, `security`, and
   * `auditor` have `read` on this module by default, every other role has none (not even
   * `read`). This deliberately mirrors the full backend grid, not only the two roles
   * ("admin and security") called out when this screen was scoped — `auditor`'s
   * blanket read-everything default (`dict.fromkeys(Module, _READ)`) includes
   * `organization_settings` too, so it belongs here as well.
   *
   * Like every other permission map in this app (see `lib/suppliers/permissions.ts`), this
   * is a **UI-only hint**: a per-user `ModulePermission` override (ADR-012) can still widen
   * what the real `GET /organizations/me` call allows, so the page always attempts the real
   * fetch and treats a 403 as a normal, handled error state rather than relying on this hint
   * to decide whether to render the panel at all.
   */
  canReadOrgPanel: boolean;
  /**
   * Can see and manage the team table (role changes, deactivation) and send invites.
   * Unlike `canReadOrgPanel` above, this does **not** mirror the general RBAC grid at all:
   * `POST/PATCH/DELETE /api/users` and `POST/GET /api/users/invites` are gated server-side
   * on `CurrentAdmin`, a dependency hardcoded to the `admin` role regardless of what a
   * per-user `ModulePermission` override might otherwise grant (see
   * `backend/app/identity/api/users.py`). A `security` or `auditor` user who can read the
   * org panel can never manage the team — no override changes that — so this is a plain
   * role check, not a grid lookup. Two different gates on one screen, from two different
   * backend rules.
   */
  canManageTeam: boolean;
}

const ORG_PANEL_READERS: ReadonlySet<Role> = new Set(["admin", "security", "auditor"]);

export function getOrganizationPermissions(role: Role): OrganizationPermissions {
  return {
    canReadOrgPanel: ORG_PANEL_READERS.has(role),
    canManageTeam: role === "admin",
  };
}
