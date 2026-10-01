import { cn } from "@/lib/cn";
import { SeverityBadge } from "./ComplianceStatusBadge";
import { EvidenceRefs } from "./EvidenceRefs";
import type { Risk, Severity } from "@/lib/compliance/types";

/** Tints the card by severity, not by a flat "this is a risk" red — a `low`-severity risk
 * shouldn't visually read as alarming as a `critical` one (persona: "Never communicate status
 * by color alone", applied in reverse: don't let one color flatten a real severity range). */
const SEVERITY_CARD_CLASSES: Record<Severity, string> = {
  critical: "border-danger-border bg-danger-surface",
  high: "border-danger-border bg-danger-surface",
  medium: "border-warning-border bg-warning-surface",
  low: "border-border bg-surface",
};

/**
 * One `Risk` — the primary "what needs attention" unit of the results screen (persona:
 * "A decision page should prioritize... Risk, Reasons, Evidence"). `category`/`description`
 * currently always mirror the triggering rule's `rule_key`/`rationale` 1:1 (see
 * `RiskResponse`'s docstring in `backend/app/policies/api/schemas.py`), so this card reads as
 * "why this risk exists," not as two generically-named wire fields.
 */
export function RiskCard({ risk }: { risk: Risk }) {
  return (
    <li className={cn("rounded-xl border p-4", SEVERITY_CARD_CLASSES[risk.severity])}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-sm font-semibold text-foreground">{risk.category}</span>
        <SeverityBadge severity={risk.severity} />
      </div>
      <p className="mt-2 text-sm text-foreground-muted">{risk.description}</p>
      <EvidenceRefs evidenceRefs={risk.evidenceRefs} />
    </li>
  );
}
