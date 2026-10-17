import { StatusBadge, statusTone } from "@/components/shared/StatusBadge";
import { TONE_RAIL_CLASSES } from "@/components/ui/Badge";
import { cn } from "@/lib/cn";
import type { RuleEvaluationRecord } from "@/lib/compliance/types";
import { EvidenceRefs } from "./EvidenceRefs";

/**
 * One evaluated rule — the POLICY half of WHY/EVIDENCE/POLICY/SOURCE, rendered for every rule
 * the engine actually evaluated (not just the ones that triggered a `Risk`), per this story's
 * full-transparency/audit requirement. REVIEW/BLOCK rows carry a tone rail so they read as
 * the ones needing attention; PASS / NOT_APPLICABLE stay neutral and quiet.
 */
export function RuleEvaluationRow({ evaluation }: { evaluation: RuleEvaluationRecord }) {
  const tone = statusTone("ruleOutcome", evaluation.outcome);
  const needsAttention = evaluation.outcome === "REVIEW" || evaluation.outcome === "BLOCK";
  return (
    <li
      className={cn(
        "border-l-2 py-1 pl-4",
        needsAttention ? TONE_RAIL_CLASSES[tone] : "border-l-border",
      )}
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex min-w-0 flex-wrap items-baseline gap-x-2">
          <span className="font-mono text-xs text-foreground-muted">{evaluation.ruleKey}</span>
          <span className="text-sm font-semibold text-foreground">{evaluation.ruleName}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <StatusBadge kind="severity" value={evaluation.severity} />
          <StatusBadge kind="ruleOutcome" value={evaluation.outcome} />
        </div>
      </div>

      <p className="mt-1 text-sm text-foreground-muted">{evaluation.rationale}</p>

      {evaluation.approverRole && (
        <p className="mt-1 text-xs text-foreground-muted">
          Requires approval from <span className="font-medium text-foreground">{evaluation.approverRole}</span>
        </p>
      )}

      <EvidenceRefs evidenceRefs={evaluation.evidenceRefs} />
    </li>
  );
}
