import {
  AlertTriangle,
  Archive,
  Ban,
  CheckCircle2,
  Clock,
  FileClock,
  FileEdit,
  Loader2,
  MinusCircle,
  RefreshCw,
  Search,
  SearchX,
  ShieldCheck,
  XCircle,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

import type { BadgeTone } from "@/components/ui/Badge";
import type { MessageKey } from "@/lib/i18n/translate";
import type { ApprovalRequestStatus } from "@/lib/approvals/types";
import type { ComplianceReviewStatus, RuleOutcome, Severity } from "@/lib/compliance/types";
import type { ContractStatus, ContractVersionStatus } from "@/lib/contracts/types";
import type { InvitationStatus, UserStatus } from "@/lib/organization/types";
import type { PolicyStatus, PolicyVersionStatus, RuleResultStatus } from "@/lib/policies/types";
import type { SupplierCheckStatus, SupplierStatus } from "@/lib/suppliers/types";

interface StatusDef {
  tone: BadgeTone;
  /** Message key of the display label (`status.<kind>.<value>` in the catalogs). */
  labelKey: MessageKey;
  icon?: LucideIcon;
  /** Spins the icon (reduced-motion safe): only for states that are genuinely in progress. */
  spin?: boolean;
}

function defs<T extends string>(map: Record<T, StatusDef>): Record<T, StatusDef> {
  return map;
}

/**
 * The single status map for the whole app: every domain status enum -> tone + icon + label.
 * Tone semantics are consistent everywhere: success = done/approved/active, warning = needs a
 * human, danger = blocked/failed, info = in progress/informational, neutral = inert/inactive.
 * Status is never color-only: each entry has a label, and most an icon too.
 *
 * APPROVE / REVIEW / BLOCK (`decision`, `ruleResult`, `ruleOutcome`) share one visual language;
 * `decision` is the aggregate outcome of a review, `ruleResult` the authored result of a rule,
 * `ruleOutcome` the evaluated outcome (adds PASS / NOT_APPLICABLE).
 */
const STATUS_MAP = {
  supplier: defs<SupplierStatus>({
    prospect: { tone: "neutral", icon: Clock, labelKey: "status.supplier.prospect" },
    under_review: { tone: "info", icon: Search, labelKey: "status.supplier.under_review" },
    approved: { tone: "success", icon: CheckCircle2, labelKey: "status.supplier.approved" },
    blocked: { tone: "danger", icon: Ban, labelKey: "status.supplier.blocked" },
    inactive: { tone: "neutral", icon: Archive, labelKey: "status.supplier.inactive" },
  }),
  supplierCheck: defs<SupplierCheckStatus>({
    started: { tone: "info", icon: Loader2, spin: true, labelKey: "status.supplierCheck.started" },
    completed: { tone: "success", icon: CheckCircle2, labelKey: "status.supplierCheck.completed" },
    failed: { tone: "danger", icon: XCircle, labelKey: "status.supplierCheck.failed" },
  }),
  contract: defs<ContractStatus>({
    draft: { tone: "neutral", icon: FileEdit, labelKey: "status.contract.draft" },
    under_review: { tone: "info", icon: Search, labelKey: "status.contract.under_review" },
    active: { tone: "success", icon: CheckCircle2, labelKey: "status.contract.active" },
    renewed: { tone: "info", icon: RefreshCw, labelKey: "status.contract.renewed" },
    terminated: { tone: "danger", icon: Ban, labelKey: "status.contract.terminated" },
    expired: { tone: "neutral", icon: Archive, labelKey: "status.contract.expired" },
  }),
  // `extracted` is a transient "processing" state, not "extraction complete" (see lib/contracts/types.ts).
  contractVersion: defs<ContractVersionStatus>({
    extracted: { tone: "neutral", icon: Loader2, spin: true, labelKey: "status.contractVersion.extracted" },
    needs_confirmation: { tone: "warning", icon: AlertTriangle, labelKey: "status.contractVersion.needs_confirmation" },
    analyzed: { tone: "success", icon: CheckCircle2, labelKey: "status.contractVersion.analyzed" },
    extraction_failed: { tone: "danger", icon: XCircle, labelKey: "status.contractVersion.extraction_failed" },
  }),
  policy: defs<PolicyStatus>({
    draft: { tone: "neutral", icon: Clock, labelKey: "status.policy.draft" },
    published: { tone: "success", icon: CheckCircle2, labelKey: "status.policy.published" },
    archived: { tone: "neutral", icon: Archive, labelKey: "status.policy.archived" },
  }),
  // A draft *version* is mutable and not yet frozen by publish (BR-POL-001) -> warning, unlike a
  // container-level policy draft, so the two stay distinguishable at a glance.
  policyVersion: defs<PolicyVersionStatus>({
    draft: { tone: "warning", icon: FileClock, labelKey: "status.policyVersion.draft" },
    published: { tone: "success", icon: ShieldCheck, labelKey: "status.policyVersion.published" },
  }),
  approvalRequest: defs<ApprovalRequestStatus>({
    pending: { tone: "warning", icon: Clock, labelKey: "status.approvalRequest.pending" },
    approved: { tone: "success", icon: CheckCircle2, labelKey: "status.approvalRequest.approved" },
    rejected: { tone: "danger", icon: XCircle, labelKey: "status.approvalRequest.rejected" },
  }),
  user: defs<UserStatus>({
    active: { tone: "success", icon: CheckCircle2, labelKey: "status.user.active" },
    pending: { tone: "info", icon: Clock, labelKey: "status.user.pending" },
    inactive: { tone: "neutral", icon: Ban, labelKey: "status.user.inactive" },
    blocked: { tone: "danger", icon: XCircle, labelKey: "status.user.blocked" },
  }),
  invitation: defs<InvitationStatus>({
    pending: { tone: "info", icon: Clock, labelKey: "status.invitation.pending" },
    accepted: { tone: "success", icon: CheckCircle2, labelKey: "status.invitation.accepted" },
    expired: { tone: "neutral", icon: Ban, labelKey: "status.invitation.expired" },
    cancelled: { tone: "danger", icon: XCircle, labelKey: "status.invitation.cancelled" },
  }),
  // The aggregate decision of a ComplianceReview ("in_progress" is never externally observable).
  decision: defs<ComplianceReviewStatus>({
    APPROVE: { tone: "success", icon: CheckCircle2, labelKey: "status.decision.APPROVE" },
    REVIEW: { tone: "warning", icon: AlertTriangle, labelKey: "status.decision.REVIEW" },
    BLOCK: { tone: "danger", icon: Ban, labelKey: "status.decision.BLOCK" },
  }),
  // The *authored* result of a policy rule.
  ruleResult: defs<RuleResultStatus>({
    APPROVE: { tone: "success", icon: CheckCircle2, labelKey: "status.ruleResult.APPROVE" },
    REVIEW: { tone: "warning", icon: AlertTriangle, labelKey: "status.ruleResult.REVIEW" },
    BLOCK: { tone: "danger", icon: Ban, labelKey: "status.ruleResult.BLOCK" },
  }),
  // The *evaluated* outcome of a rule against a contract.
  ruleOutcome: defs<RuleOutcome>({
    PASS: { tone: "success", icon: CheckCircle2, labelKey: "status.ruleOutcome.PASS" },
    REVIEW: { tone: "warning", icon: AlertTriangle, labelKey: "status.ruleOutcome.REVIEW" },
    BLOCK: { tone: "danger", icon: XCircle, labelKey: "status.ruleOutcome.BLOCK" },
    NOT_APPLICABLE: { tone: "neutral", icon: MinusCircle, labelKey: "status.ruleOutcome.NOT_APPLICABLE" },
  }),
  // Severity is a magnitude, not a decision: tone + label only, no icon. Severity never changes
  // the APPROVE/REVIEW/BLOCK aggregation (docs/03-domain/policy-engine.md).
  severity: defs<Severity>({
    critical: { tone: "danger", labelKey: "status.severity.critical" },
    high: { tone: "warning", labelKey: "status.severity.high" },
    medium: { tone: "info", labelKey: "status.severity.medium" },
    low: { tone: "neutral", labelKey: "status.severity.low" },
  }),
  verification: defs<"verified" | "mismatch" | "pending" | "not_found">({
    verified: { tone: "success", icon: CheckCircle2, labelKey: "status.verification.verified" },
    mismatch: { tone: "danger", icon: AlertTriangle, labelKey: "status.verification.mismatch" },
    pending: { tone: "info", icon: Clock, labelKey: "status.verification.pending" },
    not_found: { tone: "neutral", icon: SearchX, labelKey: "status.verification.not_found" },
  }),
} as const;

export type StatusMap = typeof STATUS_MAP;
export type StatusKind = keyof StatusMap;

export function getStatusDef<K extends StatusKind>(kind: K, value: keyof StatusMap[K]): StatusDef {
  return (STATUS_MAP[kind] as Record<PropertyKey, StatusDef>)[value as PropertyKey];
}

/** Tone for a status, for callers that tint surrounding chrome (e.g. a RiskCard's rail). */
export function statusTone<K extends StatusKind>(kind: K, value: keyof StatusMap[K]): BadgeTone {
  return getStatusDef(kind, value).tone;
}
