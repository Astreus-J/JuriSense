import { formatDateTime } from "@/lib/format";
import type { ComplianceReviewDetail } from "@/lib/compliance/types";
import { ComplianceStatusBadge } from "./ComplianceStatusBadge";
import { RiskCard } from "./RiskCard";
import { RuleEvaluationRow } from "./RuleEvaluationRow";

/**
 * #62's results screen body: WHY/EVIDENCE/POLICY/SOURCE for every triggered rule, not a bare
 * status (this story's acceptance criterion, verbatim). A Server Component — the only
 * interactive piece on the page is the native `<details>` disclosure below, which needs no
 * client-side JavaScript at all (persona: "Prefer native platform capabilities when
 * possible"; `SupplierProfileCard.tsx`'s "Raw registry data" section already establishes this
 * exact pattern in this codebase).
 *
 * Layout, in priority order (persona: "Decision first. Evidence close to the decision."):
 * 1. The decision itself (status, timing, policy coverage).
 * 2. Risks — the "what needs attention" view, one card per triggered rule.
 * 3. The full rule evaluation list — every rule the engine ran, for audit/transparency,
 *    with REVIEW/BLOCK rows expanded by default and PASS/NOT_APPLICABLE rows collapsed.
 */
export function ComplianceReviewResults({ detail }: { detail: ComplianceReviewDetail }) {
  const { review, ruleEvaluations, risks } = detail;

  const actionableEvaluations = ruleEvaluations.filter(
    (evaluation) => evaluation.outcome === "REVIEW" || evaluation.outcome === "BLOCK",
  );
  const quietEvaluations = ruleEvaluations.filter(
    (evaluation) => evaluation.outcome === "PASS" || evaluation.outcome === "NOT_APPLICABLE",
  );

  return (
    <div className="space-y-8">
      <section className="flex flex-wrap items-center gap-x-6 gap-y-2 rounded-xl border border-border bg-surface p-4">
        <ComplianceStatusBadge status={review.status} />
        <span className="text-sm text-foreground-muted">
          Started {formatDateTime(review.startedAt)}
        </span>
        <span className="text-sm text-foreground-muted">
          {review.completedAt ? `Completed ${formatDateTime(review.completedAt)}` : "Not yet completed"}
        </span>
        <span className="text-sm text-foreground-muted">
          Evaluated against {review.policyVersionIds.length} published policy version
          {review.policyVersionIds.length === 1 ? "" : "s"}
        </span>
      </section>

      <section className="space-y-3">
        <h2 className="text-sm font-semibold text-foreground">Risks</h2>

        {risks.length === 0 ? (
          <p className="rounded-xl border border-dashed border-border bg-surface px-6 py-10 text-center text-sm text-foreground-muted">
            {review.status === "APPROVE"
              ? "No risks found — all rules passed or were not applicable."
              : "No risks were recorded for this review."}
          </p>
        ) : (
          <ul className="space-y-3">
            {risks.map((risk) => (
              <RiskCard key={risk.id} risk={risk} />
            ))}
          </ul>
        )}
      </section>

      <section className="space-y-3">
        <h2 className="text-sm font-semibold text-foreground">
          Evaluated rules ({ruleEvaluations.length})
        </h2>

        {ruleEvaluations.length === 0 ? (
          <p className="rounded-xl border border-dashed border-border bg-surface px-6 py-10 text-center text-sm text-foreground-muted">
            {review.policyVersionIds.length === 0
              ? "No rules were evaluated — no policy was published in this organization yet when this review ran."
              : "No rules were evaluated — the published policy version(s) in place when this review ran had no rules defined."}
          </p>
        ) : (
          <>
            {actionableEvaluations.length > 0 && (
              <ul className="space-y-3">
                {actionableEvaluations.map((evaluation) => (
                  <RuleEvaluationRow key={evaluation.id} evaluation={evaluation} />
                ))}
              </ul>
            )}

            {quietEvaluations.length > 0 && (
              <details className="group rounded-xl border border-border bg-surface-muted">
                <summary className="cursor-pointer list-none px-4 py-3 text-sm font-medium text-foreground-muted hover:text-foreground">
                  {/* QA review (2026-10-01): this previously said "Show all N evaluated
                   * rules," overstating what the disclosure itself reveals — the REVIEW/BLOCK
                   * rows above are already visible, so opening this only adds the
                   * PASS/NOT_APPLICABLE ones. */}
                  <span className="group-open:hidden">
                    Show {quietEvaluations.length} more (passed / not applicable)
                  </span>
                  <span className="hidden group-open:inline">
                    Hide passed / not applicable rules
                  </span>
                </summary>
                <ul className="space-y-3 border-t border-border p-4">
                  {quietEvaluations.map((evaluation) => (
                    <RuleEvaluationRow key={evaluation.id} evaluation={evaluation} />
                  ))}
                </ul>
              </details>
            )}
          </>
        )}
      </section>
    </div>
  );
}
