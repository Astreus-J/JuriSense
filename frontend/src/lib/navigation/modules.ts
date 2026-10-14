import type { LucideIcon } from "lucide-react";
import {
  FileCheck2,
  Gavel,
  LayoutDashboard,
  Plug,
  Settings,
  ShieldCheck,
  Truck,
} from "lucide-react";

import type { Role } from "@/lib/auth/types";

/**
 * Primary navigation registry (STORY-1.2.1).
 *
 * Maps 1:1 to the product modules in `docs/01-product/modules.md`, with two
 * deliberate omissions from the top-level nav:
 *
 * - **Identity & Organizations** (module 1) is not a nav item; its screens
 *   (team management, plan/usage) live under "Settings", and the
 *   organization switcher itself lives in the top bar, not the primary nav.
 * - **AI Services** (module 7) is not a nav item — `docs/01-product/
 *   modules.md` itself describes it as "primarily an internal/technical
 *   transparency surface" surfaced inside Contracts/Evidence, not a
 *   standalone destination a user navigates to.
 */
export type ModuleKey =
  | "dashboard"
  | "suppliers"
  | "contracts"
  | "policies"
  | "approvals"
  | "evidence"
  | "integrations"
  | "settings";

export interface NavItem {
  key: ModuleKey;
  label: string;
  href: string;
  icon: LucideIcon;
  /** Shown on the placeholder ("coming soon") page for modules with no real UI yet. */
  comingSoonDescription?: string;
}

export const NAV_ITEMS: Record<ModuleKey, NavItem> = {
  dashboard: {
    key: "dashboard",
    label: "Dashboard",
    href: "/dashboard",
    icon: LayoutDashboard,
  },
  suppliers: {
    key: "suppliers",
    label: "Suppliers",
    href: "/suppliers",
    icon: Truck,
    comingSoonDescription:
      "Register suppliers and review their verification status against official and public sources.",
  },
  contracts: {
    key: "contracts",
    label: "Contracts",
    href: "/contracts",
    icon: FileCheck2,
    comingSoonDescription:
      "Upload contracts and review the structured, cited extraction behind every clause.",
  },
  policies: {
    key: "policies",
    label: "Policies",
    href: "/policies",
    icon: Gavel,
  },
  approvals: {
    key: "approvals",
    label: "Approvals",
    href: "/approvals",
    icon: ShieldCheck,
  },
  evidence: {
    key: "evidence",
    label: "Evidence & Audit",
    href: "/evidence",
    icon: FileCheck2,
    comingSoonDescription:
      "Every Decision Passport and the append-only audit trail behind it, in one place.",
  },
  integrations: {
    key: "integrations",
    label: "Integrations",
    href: "/integrations",
    icon: Plug,
    comingSoonDescription:
      "Connect external systems and configure outbound webhooks for lifecycle events.",
  },
  settings: {
    key: "settings",
    label: "Settings",
    href: "/settings/organization",
    icon: Settings,
  },
};

/**
 * Role → visible nav items (ADR-003's 10 roles, `docs/01-product/personas.md`).
 * This is the mapping the STORY-1.2.1 acceptance criteria asks for: "the
 * dashboard renders without error for each of the 10 roles" — every role
 * below resolves to a valid, non-empty nav list.
 *
 * #137 (2026-10-14): this list and the backend's own `DEFAULT_ROLE_GRID`
 * (`backend/app/identity/domain/rbac.py`) are two independently maintained
 * sources of truth for "which roles can see which module" — the backend's
 * `require_permission()` dependency is the real enforcement, this is only
 * what's offered as a clickable nav item. They had drifted: this file
 * omitted several modules the backend actually grants `read` on (and
 * documented that omission as deliberate, when the backend's own rationale
 * for the same role said the opposite). Reconciled below against the
 * backend grid as the authoritative source — every role now shows exactly
 * the modules it can at least `read`, with ONE documented exception
 * (`approver`, kept deliberately narrower than its read grant).
 *
 * Design rationale (backend-grounded, see `rbac.py`'s own per-role rationale
 * for the full detail):
 * - `admin`: full surface (`CRUD` everywhere in the backend grid).
 * - `procurement`: full CRUD on Suppliers/Contracts; read-only elsewhere it
 *   has visibility into (Policies, Approvals) — explicitly "needs to see the
 *   policy/compliance/approval status attached to their own suppliers/
 *   contracts" per the backend's own comment. No Evidence/Integrations/
 *   Settings (`_NONE` in the grid).
 * - `legal` / `compliance`: the two policy-authoring roles (`create`+`update`
 *   on Policies); both read Suppliers, Contracts, Evidence too.
 * - `privacy` / `security` / `finance`: each owns a category of policy rules
 *   and has an approval queue, but (per the backend's shared rationale for
 *   these five) is only ever `read` on Suppliers/Contracts/Evidence, same
 *   breadth as `legal`/`compliance`'s read-only surfaces. `security`
 *   additionally reads Integrations/Settings — "the only one of these five
 *   with that visibility" per the backend's own comment.
 * - `approver`: the one deliberate narrowing — the backend grants it `read`
 *   on Suppliers/Contracts/Policies/Evidence too, but `personas.md` is
 *   explicit that this role has "no policy-authoring or supplier/contract-
 *   management surface" and should not be "buried in low-value" surface
 *   area, so its nav stays just Dashboard + Approvals.
 * - `auditor`: read-only on *everything*, including Integrations/Settings —
 *   the backend's own comment calls these two out by name as included.
 * - `viewer`: the same read-only footprint as `legal`/`compliance`'s
 *   read-only surfaces, minus the admin/security/auditor-only
 *   Integrations/Settings.
 */
export const ROLE_NAV_ITEMS: Record<Role, ModuleKey[]> = {
  admin: [
    "dashboard",
    "suppliers",
    "contracts",
    "policies",
    "approvals",
    "evidence",
    "integrations",
    "settings",
  ],
  procurement: ["dashboard", "suppliers", "contracts", "policies", "approvals"],
  legal: ["dashboard", "suppliers", "contracts", "policies", "approvals", "evidence"],
  compliance: ["dashboard", "suppliers", "contracts", "policies", "approvals", "evidence"],
  privacy: ["dashboard", "suppliers", "contracts", "policies", "approvals", "evidence"],
  security: [
    "dashboard",
    "suppliers",
    "contracts",
    "policies",
    "approvals",
    "evidence",
    "integrations",
    "settings",
  ],
  finance: ["dashboard", "suppliers", "contracts", "policies", "approvals", "evidence"],
  // Deliberately narrower than its backend read grant -- see the rationale above.
  approver: ["dashboard", "approvals"],
  auditor: [
    "dashboard",
    "suppliers",
    "contracts",
    "policies",
    "approvals",
    "evidence",
    "integrations",
    "settings",
  ],
  viewer: ["dashboard", "suppliers", "contracts", "policies", "approvals", "evidence"],
};

export function getNavItemsForRole(role: Role): NavItem[] {
  return ROLE_NAV_ITEMS[role].map((key) => NAV_ITEMS[key]);
}
