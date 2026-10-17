import { StatusBadge } from "@/components/shared/StatusBadge";
import { statusTone } from "@/components/shared/status-map";
import { TONE_RAIL_CLASSES } from "@/components/ui/Badge";
import { cn } from "@/lib/cn";
import { EvidenceRefs } from "./EvidenceRefs";
import type { Risk } from "@/lib/compliance/types";

/**
 * One `Risk` — the primary "what needs attention" unit of the results screen (persona:
 * "A decision page should prioritize... Risk, Reasons, Evidence"). `category`/`description`
 * currently always mirror the triggering rule's `rule_key`/`rationale` 1:1 (see
 * `RiskResponse`'s docstring in `backend/app/policies/api/schemas.py`), so this reads as
 * "why this risk exists," not as two generically-named wire fields.
 *
 * Severity is carried by a left rail whose tone comes from the same `severity` status map as
 * the badge (critical->danger, high->warning, medium->info, low->neutral), so chrome and
 * badge can never disagree. A low-severity risk must not read as alarming as a critical one.
 */
export function RiskCard({ risk }: { risk: Risk }) {
  return (
    <li className={cn("border-l-2 py-1 pl-4", TONE_RAIL_CLASSES[statusTone("severity", risk.severity)])}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-sm font-semibold text-foreground">{risk.category}</span>
        <StatusBadge kind="severity" value={risk.severity} />
      </div>
      <p className="mt-1 text-sm text-foreground-muted">{risk.description}</p>
      <EvidenceRefs evidenceRefs={risk.evidenceRefs} />
    </li>
  );
}
