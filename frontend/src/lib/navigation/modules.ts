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
    comingSoonDescription:
      "Author and version the rules that turn your company's policy into an executable decision.",
  },
  approvals: {
    key: "approvals",
    label: "Approvals",
    href: "/approvals",
    icon: ShieldCheck,
    comingSoonDescription:
      "Resolve the approval requests routed to your role, with the evidence behind each one.",
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
    comingSoonDescription:
      "Manage your team, roles, plan usage, and organization details.",
  },
};

/**
 * Role → visible nav items (ADR-003's 10 roles, `docs/01-product/personas.md`).
 * This is the mapping the STORY-1.2.1 acceptance criteria asks for: "the
 * dashboard renders without error for each of the 10 roles" — every role
 * below resolves to a valid, non-empty nav list.
 *
 * Design rationale (persona-driven, see `docs/01-product/personas.md`):
 * - `admin`: full surface, including Integrations and Settings (org/team
 *   management is an admin-only action per `ADR-003`'s default grid).
 * - `procurement`: owns supplier/contract intake and tracks approval status,
 *   but does not author policy (`personas.md`, "no edit rights over
 *   Policy/Rule definitions") — Policies is intentionally omitted.
 * - `legal` / `compliance`: the two policy-authoring roles; both get
 *   Policies, Approvals, and Evidence & Audit.
 * - `privacy` / `security` / `finance`: each owns a category of policy rules
 *   and reviews the contract fields relevant to their domain, but (unlike
 *   Legal/Compliance) is not positioned as a portfolio-wide reviewer, so
 *   Evidence & Audit is left off their nav.
 * - `approver`: intentionally the narrowest — `personas.md` is explicit that
 *   this role has "no policy-authoring or supplier/contract-management
 *   surface" and should not be "buried in low-value" surface area.
 * - `auditor`: read-oriented across the whole portfolio (a GRC auditor needs
 *   to inspect suppliers/contracts/policies/approvals to do their job), with
 *   Evidence & Audit as its natural home — matching the acceptance
 *   criterion's example directly.
 * - `viewer`: the same broad read-only footprint as `auditor`, minus the
 *   admin-only Integrations/Settings surfaces.
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
  procurement: ["dashboard", "suppliers", "contracts", "approvals"],
  legal: ["dashboard", "contracts", "policies", "approvals", "evidence"],
  compliance: ["dashboard", "suppliers", "contracts", "policies", "approvals", "evidence"],
  privacy: ["dashboard", "contracts", "policies", "approvals"],
  security: ["dashboard", "contracts", "policies", "approvals"],
  finance: ["dashboard", "contracts", "policies", "approvals"],
  approver: ["dashboard", "approvals"],
  auditor: ["dashboard", "suppliers", "contracts", "policies", "approvals", "evidence"],
  viewer: ["dashboard", "suppliers", "contracts", "policies", "approvals", "evidence"],
};

export function getNavItemsForRole(role: Role): NavItem[] {
  return ROLE_NAV_ITEMS[role].map((key) => NAV_ITEMS[key]);
}
