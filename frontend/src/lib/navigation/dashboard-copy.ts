import type { LucideIcon } from "lucide-react";
import { FileCheck2, Gavel, ShieldCheck, Truck } from "lucide-react";

import type { Role } from "@/lib/auth/types";
import type { Messages } from "@/lib/i18n/messages/en";
import type { ModuleKey } from "./modules";

/** Key into `dashboard.highlights` in the message catalogs (title + description). */
export type HighlightId = keyof Messages["dashboard"]["highlights"];

export interface RoleHighlight {
  moduleKey: ModuleKey;
  icon: LucideIcon;
  id: HighlightId;
}

/**
 * Per-role dashboard structure (STORY-1.2.1's "role-appropriate empty dashboard").
 *
 * Everything in the product is empty on day one — there are no suppliers,
 * contracts, or policies yet, because this story only builds the shell. Per
 * the frontend-engineer persona's empty-state standard, that "empty" state
 * still has to say what's empty, why, and what to do next, tailored to what
 * each role in `docs/01-product/personas.md` actually does — not a single
 * generic "Welcome!" screen repeated for all 10 roles.
 *
 * Only the structure (which modules/icons each role is pointed at) lives here; the visible
 * copy -- the role headline/subtext (`dashboard.roles.<role>`) and each highlight's
 * title/description (`dashboard.highlights.<id>`) -- lives in the message catalogs.
 */
export const ROLE_DASHBOARD_HIGHLIGHTS: Record<Role, RoleHighlight[]> = {
  admin: [
    { moduleKey: "settings", icon: ShieldCheck, id: "adminInviteTeam" },
    { moduleKey: "suppliers", icon: Truck, id: "adminFirstSupplier" },
    { moduleKey: "policies", icon: Gavel, id: "adminFirstPolicy" },
  ],
  procurement: [
    { moduleKey: "suppliers", icon: Truck, id: "procurementRegisterSupplier" },
    { moduleKey: "contracts", icon: FileCheck2, id: "procurementUploadContract" },
    { moduleKey: "approvals", icon: ShieldCheck, id: "procurementTrackApprovals" },
  ],
  legal: [
    { moduleKey: "policies", icon: Gavel, id: "legalAuthorPolicy" },
    { moduleKey: "contracts", icon: FileCheck2, id: "legalReviewContracts" },
    { moduleKey: "approvals", icon: ShieldCheck, id: "legalResolveApprovals" },
  ],
  compliance: [
    { moduleKey: "policies", icon: Gavel, id: "complianceOwnRules" },
    { moduleKey: "evidence", icon: FileCheck2, id: "complianceInvestigate" },
    { moduleKey: "approvals", icon: ShieldCheck, id: "complianceResolveApprovals" },
  ],
  privacy: [
    { moduleKey: "policies", icon: Gavel, id: "privacyAuthorRules" },
    { moduleKey: "contracts", icon: FileCheck2, id: "privacyReviewTerms" },
    { moduleKey: "approvals", icon: ShieldCheck, id: "privacyResolveApprovals" },
  ],
  security: [
    { moduleKey: "policies", icon: Gavel, id: "securityAuthorRules" },
    { moduleKey: "contracts", icon: FileCheck2, id: "securityReviewTerms" },
    { moduleKey: "approvals", icon: ShieldCheck, id: "securityResolveApprovals" },
  ],
  finance: [
    { moduleKey: "policies", icon: Gavel, id: "financeSetThresholds" },
    { moduleKey: "contracts", icon: FileCheck2, id: "financeReviewTerms" },
    { moduleKey: "approvals", icon: ShieldCheck, id: "financeResolveApprovals" },
  ],
  approver: [{ moduleKey: "approvals", icon: ShieldCheck, id: "approverQueue" }],
  auditor: [
    { moduleKey: "evidence", icon: FileCheck2, id: "auditorTrail" },
    { moduleKey: "approvals", icon: ShieldCheck, id: "auditorApprovalHistory" },
    { moduleKey: "policies", icon: Gavel, id: "auditorPolicyHistory" },
  ],
  viewer: [
    { moduleKey: "suppliers", icon: Truck, id: "viewerSuppliers" },
    { moduleKey: "contracts", icon: FileCheck2, id: "viewerContracts" },
  ],
};
