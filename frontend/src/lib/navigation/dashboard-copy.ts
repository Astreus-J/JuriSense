import type { LucideIcon } from "lucide-react";
import { FileCheck2, Gavel, ShieldCheck, Truck } from "lucide-react";

import type { Role } from "@/lib/auth/types";
import type { ModuleKey } from "./modules";

export interface RoleHighlight {
  moduleKey: ModuleKey;
  icon: LucideIcon;
  title: string;
  description: string;
}

export interface RoleDashboardCopy {
  roleLabel: string;
  headline: string;
  subtext: string;
  highlights: RoleHighlight[];
}

/**
 * Per-role dashboard copy (STORY-1.2.1's "role-appropriate empty dashboard").
 *
 * Everything in the product is empty on day one — there are no suppliers,
 * contracts, or policies yet, because this story only builds the shell. Per
 * the frontend-engineer persona's empty-state standard, that "empty" state
 * still has to say what's empty, why, and what to do next, tailored to what
 * each role in `docs/01-product/personas.md` actually does — not a single
 * generic "Welcome!" screen repeated for all 10 roles.
 */
export const ROLE_DASHBOARD_COPY: Record<Role, RoleDashboardCopy> = {
  admin: {
    roleLabel: "Admin",
    headline: "Set up your organization",
    subtext:
      "You're the first person here. Invite your team and they'll land in the right place based on their role.",
    highlights: [
      {
        moduleKey: "settings",
        icon: ShieldCheck,
        title: "Invite your team",
        description: "Add Procurement, Legal, Compliance, and other teammates with the right role.",
      },
      {
        moduleKey: "suppliers",
        icon: Truck,
        title: "Register your first supplier",
        description: "Start the pipeline: supplier verification, contract upload, and review.",
      },
      {
        moduleKey: "policies",
        icon: Gavel,
        title: "Author your first policy",
        description: "Turn a standing rule (e.g. \"require a liability cap\") into an executable check.",
      },
    ],
  },
  procurement: {
    roleLabel: "Procurement",
    headline: "No suppliers yet",
    subtext:
      "Once you register a supplier and upload a contract, you'll track its status here instead of a spreadsheet.",
    highlights: [
      {
        moduleKey: "suppliers",
        icon: Truck,
        title: "Register a supplier",
        description: "Start a verification check as soon as a vendor relationship begins.",
      },
      {
        moduleKey: "contracts",
        icon: FileCheck2,
        title: "Upload a contract",
        description: "Get a structured, cited extraction instead of a 40-page PDF.",
      },
      {
        moduleKey: "approvals",
        icon: ShieldCheck,
        title: "Track approvals",
        description: "See exactly where a review sits and who it's waiting on.",
      },
    ],
  },
  legal: {
    roleLabel: "Legal",
    headline: "No contracts to review yet",
    subtext:
      "As contracts come in, flagged clauses will show up here with page/span citations — no more hunting through PDFs.",
    highlights: [
      {
        moduleKey: "policies",
        icon: Gavel,
        title: "Author your policy",
        description: "Encode what \"acceptable\" means (liability caps, jurisdiction, indemnification).",
      },
      {
        moduleKey: "contracts",
        icon: FileCheck2,
        title: "Review contracts",
        description: "Go straight to the clauses that need judgment, cited back to the source.",
      },
      {
        moduleKey: "approvals",
        icon: ShieldCheck,
        title: "Resolve approvals",
        description: "Requests routed to Legal will appear in your queue, sorted by severity.",
      },
    ],
  },
  compliance: {
    roleLabel: "Compliance",
    headline: "No compliance reviews yet",
    subtext:
      "Once reviews start running, you'll see outcomes across the whole portfolio here, not one contract at a time.",
    highlights: [
      {
        moduleKey: "policies",
        icon: Gavel,
        title: "Own the rule set",
        description: "Sanctions and regulatory rules, versioned and simulated before publishing.",
      },
      {
        moduleKey: "evidence",
        icon: FileCheck2,
        title: "Investigate outcomes",
        description: "Every BLOCK/REVIEW comes with WHY, EVIDENCE, and SOURCE attached.",
      },
      {
        moduleKey: "approvals",
        icon: ShieldCheck,
        title: "Resolve approvals",
        description: "Requests routed to Compliance will appear in your queue.",
      },
    ],
  },
  privacy: {
    roleLabel: "Privacy",
    headline: "No vendors processing personal data yet",
    subtext:
      "As contracts are analyzed, the ones that process personal data — and whether a DPA is in place — will show up here.",
    highlights: [
      {
        moduleKey: "policies",
        icon: Gavel,
        title: "Author LGPD rules",
        description: "E.g. require a DPA whenever a contract processes personal data.",
      },
      {
        moduleKey: "contracts",
        icon: FileCheck2,
        title: "Review data-processing terms",
        description: "See which contracts process personal data and under what basis.",
      },
      {
        moduleKey: "approvals",
        icon: ShieldCheck,
        title: "Resolve approvals",
        description: "Requests routed to Privacy will appear in your queue.",
      },
    ],
  },
  security: {
    roleLabel: "Security",
    headline: "No vendors reviewed for security posture yet",
    subtext:
      "Once contracts are analyzed, certifications, breach-notification terms, and access scope will show up here.",
    highlights: [
      {
        moduleKey: "policies",
        icon: Gavel,
        title: "Author security rules",
        description: "Minimum certifications or breach-notification SLAs by data-access tier.",
      },
      {
        moduleKey: "contracts",
        icon: FileCheck2,
        title: "Review security terms",
        description: "Certifications, sub-processors, and breach-notification clauses.",
      },
      {
        moduleKey: "approvals",
        icon: ShieldCheck,
        title: "Resolve approvals",
        description: "Requests routed to Security will appear in your queue.",
      },
    ],
  },
  finance: {
    roleLabel: "Finance",
    headline: "No financial exposure tracked yet",
    subtext:
      "As contracts are signed, value, renewal, and penalty terms will roll up here instead of showing up as invoice surprises.",
    highlights: [
      {
        moduleKey: "policies",
        icon: Gavel,
        title: "Set value thresholds",
        description: "E.g. contracts above a value require Legal, or Legal + Director, review.",
      },
      {
        moduleKey: "contracts",
        icon: FileCheck2,
        title: "Review financial terms",
        description: "Value, currency, renewal terms, and penalty clauses, structured and queryable.",
      },
      {
        moduleKey: "approvals",
        icon: ShieldCheck,
        title: "Resolve approvals",
        description: "Requests routed to Finance will appear in your queue.",
      },
    ],
  },
  approver: {
    roleLabel: "Approver",
    headline: "No approvals waiting on you",
    subtext:
      "You'll only see requests here when your decision is genuinely required — a synthesized summary, not the raw contract.",
    highlights: [
      {
        moduleKey: "approvals",
        icon: ShieldCheck,
        title: "Your approval queue",
        description: "WHY, evidence, and risk — built for a 2–5 minute, well-informed decision.",
      },
    ],
  },
  auditor: {
    roleLabel: "Auditor",
    headline: "No audit trail yet",
    subtext:
      "As the organization starts operating, every meaningful action will appear here as an append-only, unfalsifiable record.",
    highlights: [
      {
        moduleKey: "evidence",
        icon: FileCheck2,
        title: "Audit trail",
        description: "A chronological, filterable log of every state-changing action.",
      },
      {
        moduleKey: "approvals",
        icon: ShieldCheck,
        title: "Approval history",
        description: "Every decision, its evidence, and who resolved it.",
      },
      {
        moduleKey: "policies",
        icon: Gavel,
        title: "Policy history",
        description: "Every published policy version the organization has ever evaluated against.",
      },
    ],
  },
  viewer: {
    roleLabel: "Viewer",
    headline: "Nothing to show yet",
    subtext:
      "You have read access across the organization's suppliers, contracts, policies, and approvals — they'll show up here once they exist.",
    highlights: [
      {
        moduleKey: "suppliers",
        icon: Truck,
        title: "Suppliers",
        description: "Read-only visibility into the supplier registry once it exists.",
      },
      {
        moduleKey: "contracts",
        icon: FileCheck2,
        title: "Contracts",
        description: "Read-only visibility into contract review outcomes once they exist.",
      },
    ],
  },
};
