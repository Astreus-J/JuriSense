import { Badge } from "@/components/ui/Badge";
import type { BadgeTone } from "@/components/ui/Badge";
import { SEVERITY_LABELS } from "@/lib/policies/types";
import type { Severity } from "@/lib/policies/types";

const TONE_CONFIG: Record<Severity, BadgeTone> = {
  critical: "danger",
  high: "warning",
  medium: "info",
  low: "neutral",
};

/**
 * Severity never changes a rule's APPROVE/REVIEW/BLOCK aggregation
 * (`docs/03-domain/policy-engine.md` "Severity & escalation") — it only breaks ties among
 * simultaneous REVIEW rules and prioritizes a reviewer's queue — so it's rendered as its
 * own plain pill rather than reusing `RuleOutcomeBadge`'s decision-outcome styling, to
 * avoid implying severity is a second decision signal.
 */
export function SeverityBadge({ severity }: { severity: Severity }) {
  return <Badge tone={TONE_CONFIG[severity]}>{SEVERITY_LABELS[severity]}</Badge>;
}
