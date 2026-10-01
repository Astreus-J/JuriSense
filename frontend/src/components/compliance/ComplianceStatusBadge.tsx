import { AlertTriangle, Ban, CheckCircle2, MinusCircle, XCircle } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { Badge } from "@/components/ui/Badge";
import type { BadgeTone } from "@/components/ui/Badge";
import {
  COMPLIANCE_REVIEW_STATUS_LABELS,
  RULE_OUTCOME_LABELS,
  SEVERITY_LABELS,
} from "@/lib/compliance/types";
import type { ComplianceReviewStatus, RuleOutcome, Severity } from "@/lib/compliance/types";

const REVIEW_STATUS_CONFIG: Record<ComplianceReviewStatus, { tone: BadgeTone; icon: LucideIcon }> = {
  APPROVE: { tone: "success", icon: CheckCircle2 },
  REVIEW: { tone: "warning", icon: AlertTriangle },
  BLOCK: { tone: "danger", icon: Ban },
};

/** A `ComplianceReview`'s terminal decision — `"in_progress"` is never externally observable
 * (`trigger_review` runs synchronously), so there is no "processing" tone to model here. */
export function ComplianceStatusBadge({ status }: { status: ComplianceReviewStatus }) {
  const { tone, icon: Icon } = REVIEW_STATUS_CONFIG[status];
  return (
    <Badge tone={tone} icon={<Icon className="size-3.5" aria-hidden="true" />}>
      {COMPLIANCE_REVIEW_STATUS_LABELS[status]}
    </Badge>
  );
}

const OUTCOME_CONFIG: Record<RuleOutcome, { tone: BadgeTone; icon: LucideIcon }> = {
  PASS: { tone: "success", icon: CheckCircle2 },
  REVIEW: { tone: "warning", icon: AlertTriangle },
  BLOCK: { tone: "danger", icon: XCircle },
  NOT_APPLICABLE: { tone: "neutral", icon: MinusCircle },
};

/** One `RuleEvaluation.outcome` — the POLICY half of WHY/EVIDENCE/POLICY/SOURCE. */
export function RuleOutcomeBadge({ outcome }: { outcome: RuleOutcome }) {
  const { tone, icon: Icon } = OUTCOME_CONFIG[outcome];
  return (
    <Badge tone={tone} icon={<Icon className="size-3.5" aria-hidden="true" />}>
      {RULE_OUTCOME_LABELS[outcome]}
    </Badge>
  );
}

const SEVERITY_TONE: Record<Severity, BadgeTone> = {
  critical: "danger",
  high: "warning",
  medium: "info",
  low: "neutral",
};

/** `RuleEvaluation`/`Risk` severity. No icon, unlike the two badges above: severity is a
 * magnitude on a scale, not a discrete state, so a plain tone+label pill reads more calmly
 * next to an outcome badge than a second icon would (persona: "status is never color-only" —
 * satisfied here by the label, since severity already has its own adjacent outcome icon). */
export function SeverityBadge({ severity }: { severity: Severity }) {
  return <Badge tone={SEVERITY_TONE[severity]}>{SEVERITY_LABELS[severity]}</Badge>;
}
