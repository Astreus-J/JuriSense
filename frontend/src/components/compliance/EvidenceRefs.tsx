import { describeEvidenceRef } from "@/lib/compliance/evidence";
import type { EvidenceRef } from "@/lib/compliance/types";
import { getI18n } from "@/lib/i18n/server";

/**
 * Renders the SOURCE half of WHY/EVIDENCE/POLICY/SOURCE — one line per evidence ref, as plain
 * text (persona: "Don't over-engineer document viewing — no document viewer exists yet").
 * Used by both `RiskCard` and `RuleEvaluationRow` so the two never drift in how they cite
 * their evidence.
 */
export async function EvidenceRefs({ evidenceRefs }: { evidenceRefs: EvidenceRef[] }) {
  if (evidenceRefs.length === 0) return null;
  const i18n = await getI18n();
  return (
    <ul className="mt-1.5 space-y-0.5">
      {evidenceRefs.map((ref, index) => (
        <li key={index} className="text-xs text-foreground-muted">
          <span className="font-medium">{i18n.t("compliance.evidence.source")}</span> ·{" "}
          {describeEvidenceRef(ref, i18n)}
        </li>
      ))}
    </ul>
  );
}
