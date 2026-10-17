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

import { Badge, TONE_TEXT_CLASSES } from "@/components/ui/Badge";
import type { BadgeTone } from "@/components/ui/Badge";
import { cn } from "@/lib/cn";
import { APPROVAL_REQUEST_STATUS_LABELS } from "@/lib/approvals/types";
import type { ApprovalRequestStatus } from "@/lib/approvals/types";
import {
  COMPLIANCE_REVIEW_STATUS_LABELS,
  RULE_OUTCOME_LABELS,
  SEVERITY_LABELS,
} from "@/lib/compliance/types";
import type { ComplianceReviewStatus, RuleOutcome, Severity } from "@/lib/compliance/types";
import {
  CONTRACT_STATUS_LABELS,
  CONTRACT_VERSION_STATUS_LABELS,
} from "@/lib/contracts/types";
import type { ContractStatus, ContractVersionStatus } from "@/lib/contracts/types";
import { INVITATION_STATUS_LABELS, USER_STATUS_LABELS } from "@/lib/organization/types";
import type { InvitationStatus, UserStatus } from "@/lib/organization/types";
import {
  POLICY_STATUS_LABELS,
  POLICY_VERSION_STATUS_LABELS,
  RULE_RESULT_STATUS_LABELS,
} from "@/lib/policies/types";
import type { PolicyStatus, PolicyVersionStatus, RuleResultStatus } from "@/lib/policies/types";
import { SUPPLIER_CHECK_STATUS_LABELS, SUPPLIER_STATUS_LABELS } from "@/lib/suppliers/types";
import type { SupplierCheckStatus, SupplierStatus } from "@/lib/suppliers/types";

interface StatusDef {
  tone: BadgeTone;
  label: string;
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
    prospect: { tone: "neutral", icon: Clock, label: SUPPLIER_STATUS_LABELS.prospect },
    under_review: { tone: "info", icon: Search, label: SUPPLIER_STATUS_LABELS.under_review },
    approved: { tone: "success", icon: CheckCircle2, label: SUPPLIER_STATUS_LABELS.approved },
    blocked: { tone: "danger", icon: Ban, label: SUPPLIER_STATUS_LABELS.blocked },
    inactive: { tone: "neutral", icon: Archive, label: SUPPLIER_STATUS_LABELS.inactive },
  }),
  supplierCheck: defs<SupplierCheckStatus>({
    started: { tone: "info", icon: Loader2, spin: true, label: SUPPLIER_CHECK_STATUS_LABELS.started },
    completed: { tone: "success", icon: CheckCircle2, label: SUPPLIER_CHECK_STATUS_LABELS.completed },
    failed: { tone: "danger", icon: XCircle, label: SUPPLIER_CHECK_STATUS_LABELS.failed },
  }),
  contract: defs<ContractStatus>({
    draft: { tone: "neutral", icon: FileEdit, label: CONTRACT_STATUS_LABELS.draft },
    under_review: { tone: "info", icon: Search, label: CONTRACT_STATUS_LABELS.under_review },
    active: { tone: "success", icon: CheckCircle2, label: CONTRACT_STATUS_LABELS.active },
    renewed: { tone: "info", icon: RefreshCw, label: CONTRACT_STATUS_LABELS.renewed },
    terminated: { tone: "danger", icon: Ban, label: CONTRACT_STATUS_LABELS.terminated },
    expired: { tone: "neutral", icon: Archive, label: CONTRACT_STATUS_LABELS.expired },
  }),
  // `extracted` is a transient "processing" state, not "extraction complete" (see lib/contracts/types.ts).
  contractVersion: defs<ContractVersionStatus>({
    extracted: { tone: "neutral", icon: Loader2, spin: true, label: CONTRACT_VERSION_STATUS_LABELS.extracted },
    needs_confirmation: { tone: "warning", icon: AlertTriangle, label: CONTRACT_VERSION_STATUS_LABELS.needs_confirmation },
    analyzed: { tone: "success", icon: CheckCircle2, label: CONTRACT_VERSION_STATUS_LABELS.analyzed },
    extraction_failed: { tone: "danger", icon: XCircle, label: CONTRACT_VERSION_STATUS_LABELS.extraction_failed },
  }),
  policy: defs<PolicyStatus>({
    draft: { tone: "neutral", icon: Clock, label: POLICY_STATUS_LABELS.draft },
    published: { tone: "success", icon: CheckCircle2, label: POLICY_STATUS_LABELS.published },
    archived: { tone: "neutral", icon: Archive, label: POLICY_STATUS_LABELS.archived },
  }),
  // A draft *version* is mutable and not yet frozen by publish (BR-POL-001) -> warning, unlike a
  // container-level policy draft, so the two stay distinguishable at a glance.
  policyVersion: defs<PolicyVersionStatus>({
    draft: { tone: "warning", icon: FileClock, label: POLICY_VERSION_STATUS_LABELS.draft },
    published: { tone: "success", icon: ShieldCheck, label: POLICY_VERSION_STATUS_LABELS.published },
  }),
  approvalRequest: defs<ApprovalRequestStatus>({
    pending: { tone: "warning", icon: Clock, label: APPROVAL_REQUEST_STATUS_LABELS.pending },
    approved: { tone: "success", icon: CheckCircle2, label: APPROVAL_REQUEST_STATUS_LABELS.approved },
    rejected: { tone: "danger", icon: XCircle, label: APPROVAL_REQUEST_STATUS_LABELS.rejected },
  }),
  user: defs<UserStatus>({
    active: { tone: "success", icon: CheckCircle2, label: USER_STATUS_LABELS.active },
    pending: { tone: "info", icon: Clock, label: USER_STATUS_LABELS.pending },
    inactive: { tone: "neutral", icon: Ban, label: USER_STATUS_LABELS.inactive },
    blocked: { tone: "danger", icon: XCircle, label: USER_STATUS_LABELS.blocked },
  }),
  invitation: defs<InvitationStatus>({
    pending: { tone: "info", icon: Clock, label: INVITATION_STATUS_LABELS.pending },
    accepted: { tone: "success", icon: CheckCircle2, label: INVITATION_STATUS_LABELS.accepted },
    expired: { tone: "neutral", icon: Ban, label: INVITATION_STATUS_LABELS.expired },
    cancelled: { tone: "danger", icon: XCircle, label: INVITATION_STATUS_LABELS.cancelled },
  }),
  // The aggregate decision of a ComplianceReview ("in_progress" is never externally observable).
  decision: defs<ComplianceReviewStatus>({
    APPROVE: { tone: "success", icon: CheckCircle2, label: COMPLIANCE_REVIEW_STATUS_LABELS.APPROVE },
    REVIEW: { tone: "warning", icon: AlertTriangle, label: COMPLIANCE_REVIEW_STATUS_LABELS.REVIEW },
    BLOCK: { tone: "danger", icon: Ban, label: COMPLIANCE_REVIEW_STATUS_LABELS.BLOCK },
  }),
  // The *authored* result of a policy rule.
  ruleResult: defs<RuleResultStatus>({
    APPROVE: { tone: "success", icon: CheckCircle2, label: RULE_RESULT_STATUS_LABELS.APPROVE },
    REVIEW: { tone: "warning", icon: AlertTriangle, label: RULE_RESULT_STATUS_LABELS.REVIEW },
    BLOCK: { tone: "danger", icon: Ban, label: RULE_RESULT_STATUS_LABELS.BLOCK },
  }),
  // The *evaluated* outcome of a rule against a contract.
  ruleOutcome: defs<RuleOutcome>({
    PASS: { tone: "success", icon: CheckCircle2, label: RULE_OUTCOME_LABELS.PASS },
    REVIEW: { tone: "warning", icon: AlertTriangle, label: RULE_OUTCOME_LABELS.REVIEW },
    BLOCK: { tone: "danger", icon: XCircle, label: RULE_OUTCOME_LABELS.BLOCK },
    NOT_APPLICABLE: { tone: "neutral", icon: MinusCircle, label: RULE_OUTCOME_LABELS.NOT_APPLICABLE },
  }),
  // Severity is a magnitude, not a decision: tone + label only, no icon. Severity never changes
  // the APPROVE/REVIEW/BLOCK aggregation (docs/03-domain/policy-engine.md).
  severity: defs<Severity>({
    critical: { tone: "danger", label: SEVERITY_LABELS.critical },
    high: { tone: "warning", label: SEVERITY_LABELS.high },
    medium: { tone: "info", label: SEVERITY_LABELS.medium },
    low: { tone: "neutral", label: SEVERITY_LABELS.low },
  }),
  verification: defs<"verified" | "mismatch" | "pending" | "not_found">({
    verified: { tone: "success", icon: CheckCircle2, label: "Verified" },
    mismatch: { tone: "danger", icon: AlertTriangle, label: "Mismatch" },
    pending: { tone: "info", icon: Clock, label: "Pending" },
    not_found: { tone: "neutral", icon: SearchX, label: "Not found" },
  }),
} as const;

type StatusMap = typeof STATUS_MAP;
export type StatusKind = keyof StatusMap;

function getDef<K extends StatusKind>(kind: K, value: keyof StatusMap[K]): StatusDef {
  return (STATUS_MAP[kind] as Record<PropertyKey, StatusDef>)[value as PropertyKey];
}

/** Tone for a status, for callers that tint surrounding chrome (e.g. a RiskCard's rail). */
export function statusTone<K extends StatusKind>(kind: K, value: keyof StatusMap[K]): BadgeTone {
  return getDef(kind, value).tone;
}

/**
 * The prominent form of a decision (APPROVE / REVIEW / BLOCK): large icon + label in the
 * decision's tone, no pill. Used where the decision IS the page's answer (review results,
 * Decision Passport). Smaller contexts use `StatusBadge kind="decision"`.
 */
export function DecisionMark({
  value,
  caption,
}: {
  value: keyof StatusMap["decision"];
  caption?: string;
}) {
  const { tone, label, icon: Icon } = getDef("decision", value);
  return (
    <div className="flex items-center gap-3">
      {Icon && <Icon className={cn("size-8 shrink-0", TONE_TEXT_CLASSES[tone])} aria-hidden="true" />}
      <div className="leading-tight">
        {caption && <p className="text-xs text-foreground-muted">{caption}</p>}
        <p className={cn("font-serif text-xl font-semibold", TONE_TEXT_CLASSES[tone])}>{label}</p>
      </div>
    </div>
  );
}

/**
 * Renders any domain status as a Badge from the single `STATUS_MAP`. A Server Component:
 * icons are rendered into markup here, never passed across the Server->Client boundary.
 */
export function StatusBadge<K extends StatusKind>({
  kind,
  value,
  className,
}: {
  kind: K;
  value: keyof StatusMap[K];
  className?: string;
}) {
  const { tone, label, icon: Icon, spin } = getDef(kind, value);
  return (
    <Badge
      tone={tone}
      className={className}
      icon={
        Icon ? (
          <Icon
            className={spin ? "size-3 motion-safe:animate-spin" : "size-3"}
            aria-hidden="true"
          />
        ) : undefined
      }
    >
      {label}
    </Badge>
  );
}
