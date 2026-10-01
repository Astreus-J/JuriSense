import { cn } from "@/lib/cn";
import type { RuleEvaluationRecord, RuleOutcome } from "@/lib/compliance/types";
import { RuleOutcomeBadge, SeverityBadge } from "./ComplianceStatusBadge";
import { EvidenceRefs } from "./EvidenceRefs";

/** `REVIEW`/`BLOCK` rows get a tinted border so they read as the ones needing attention even
 * inside the always-visible, un-collapsed group (persona: "REVIEW/BLOCK rows should be
 * visually prominent"). `PASS`/`NOT_APPLICABLE` get a plain, de-emphasized treatment — they
 * only render inside the "show all evaluated rules" disclosure. */
const CONTAINER_CLASSES: Record<RuleOutcome, string> = {
  PASS: "border-border bg-surface",
  NOT_APPLICABLE: "border-border bg-surface",
  REVIEW: "border-warning-border bg-warning-surface",
  BLOCK: "border-danger-border bg-danger-surface",
};

/**
 * One evaluated rule — the POLICY half of WHY/EVIDENCE/POLICY/SOURCE, rendered for every rule
 * the engine actually evaluated (not just the ones that triggered a `Risk`), per this story's
 * full-transparency/audit requirement.
 */
export function RuleEvaluationRow({ evaluation }: { evaluation: RuleEvaluationRecord }) {
  return (
    <li className={cn("rounded-xl border p-4", CONTAINER_CLASSES[evaluation.outcome])}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-mono text-xs font-semibold text-foreground-muted">
            {evaluation.ruleKey}
          </span>
          <span className="text-sm font-semibold text-foreground">{evaluation.ruleName}</span>
        </div>
        <div className="flex items-center gap-2">
          <SeverityBadge severity={evaluation.severity} />
          <RuleOutcomeBadge outcome={evaluation.outcome} />
        </div>
      </div>

      <p className="mt-2 text-sm text-foreground-muted">{evaluation.rationale}</p>

      {evaluation.approverRole && (
        <p className="mt-1 text-xs font-medium text-foreground-muted">
          Requires approval from: {evaluation.approverRole}
        </p>
      )}

      <EvidenceRefs evidenceRefs={evaluation.evidenceRefs} />
    </li>
  );
}
