import { AlertTriangle, Ban, CheckCircle2 } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { Badge } from "@/components/ui/Badge";
import type { BadgeTone } from "@/components/ui/Badge";
import { RULE_RESULT_STATUS_LABELS } from "@/lib/policies/types";
import type { RuleResultStatus } from "@/lib/policies/types";

/**
 * APPROVE/REVIEW/BLOCK are critical product states (persona: "Decision UX") — each gets a
 * visually distinct tone + icon + label, never color alone, matching the same tri-state
 * styling this product uses for a `ComplianceReview`'s own aggregate outcome
 * (`components/compliance/ComplianceStatusBadge`) so a rule's *authored* result (this
 * badge) reads consistently with the *evaluated* outcome it produces at review time.
 * Deliberately named `RuleResultBadge`, not `RuleOutcomeBadge` — that name is already
 * `components/compliance/ComplianceStatusBadge.tsx`'s export for the distinct
 * `RuleEvaluation.outcome` type (`PASS`/`REVIEW`/`BLOCK`/`NOT_APPLICABLE`, a superset
 * produced by evaluating this rule, not authoring it); reusing the name here for a
 * different type in a different module would invite exactly the mix-up this comment is
 * now preventing.
 */
const STATUS_CONFIG: Record<RuleResultStatus, { tone: BadgeTone; icon: LucideIcon }> = {
  APPROVE: { tone: "success", icon: CheckCircle2 },
  REVIEW: { tone: "warning", icon: AlertTriangle },
  BLOCK: { tone: "danger", icon: Ban },
};

export function RuleResultBadge({ status }: { status: RuleResultStatus }) {
  const { tone, icon: Icon } = STATUS_CONFIG[status];
  return (
    <Badge tone={tone} icon={<Icon className="size-3.5" aria-hidden="true" />}>
      {RULE_RESULT_STATUS_LABELS[status]}
    </Badge>
  );
}
