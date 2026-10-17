import { describeEvidenceRef } from "@/lib/compliance/evidence";
import type { EvidenceRef } from "@/lib/compliance/types";

/**
 * Renders the SOURCE half of WHY/EVIDENCE/POLICY/SOURCE — one line per evidence ref, as plain
 * text (persona: "Don't over-engineer document viewing — no document viewer exists yet").
 * Used by both `RiskCard` and `RuleEvaluationRow` so the two never drift in how they cite
 * their evidence.
 */
export function EvidenceRefs({ evidenceRefs }: { evidenceRefs: EvidenceRef[] }) {
  if (evidenceRefs.length === 0) return null;
  return (
    <ul className="mt-1.5 space-y-0.5">
      {evidenceRefs.map((ref, index) => (
        <li key={index} className="text-xs text-foreground-muted">
          <span className="font-medium">Source</span> · {describeEvidenceRef(ref)}
        </li>
      ))}
    </ul>
  );
}
