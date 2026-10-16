import { DecisionMark } from "@/components/shared/StatusBadge";
import { EmptyState } from "@/components/ui/EmptyState";
import { formatDateTime } from "@/lib/format";
import type { ComplianceReviewDetail } from "@/lib/compliance/types";
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
      <section
        aria-label="Decision"
        className="flex flex-wrap items-center justify-between gap-x-8 gap-y-3 border-b border-border pb-5"
      >
        <DecisionMark value={review.status} caption="Decision" />
        <dl className="grid grid-cols-2 gap-x-8 gap-y-1 text-sm sm:grid-cols-3">
          <div>
            <dt className="text-xs text-foreground-muted">Started</dt>
            <dd className="tabular-nums">{formatDateTime(review.startedAt)}</dd>
          </div>
          <div>
            <dt className="text-xs text-foreground-muted">Completed</dt>
            <dd className="tabular-nums">
              {review.completedAt ? formatDateTime(review.completedAt) : "Not yet completed"}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-foreground-muted">Policy coverage</dt>
            <dd className="tabular-nums">
              {review.policyVersionIds.length} published version
              {review.policyVersionIds.length === 1 ? "" : "s"}
            </dd>
          </div>
        </dl>
      </section>

      <section className="space-y-3">
        <h2 className="text-base font-semibold text-foreground">Risks</h2>

        {risks.length === 0 ? (
          <EmptyState
            title={review.status === "APPROVE" ? "No risks found" : "No risks recorded"}
            description={
              review.status === "APPROVE"
                ? "All rules passed or were not applicable."
                : "No risks were recorded for this review."
            }
          />
        ) : (
          <ul className="space-y-4">
            {risks.map((risk) => (
              <RiskCard key={risk.id} risk={risk} />
            ))}
          </ul>
        )}
      </section>

      <section className="space-y-3">
        <h2 className="text-base font-semibold text-foreground">
          Evaluated rules <span className="font-normal tabular-nums text-foreground-muted">({ruleEvaluations.length})</span>
        </h2>

        {ruleEvaluations.length === 0 ? (
          <EmptyState
            title="No rules were evaluated"
            description={
              review.policyVersionIds.length === 0
                ? "No policy was published in this organization yet when this review ran."
                : "The published policy version(s) in place when this review ran had no rules defined."
            }
          />
        ) : (
          <>
            {actionableEvaluations.length > 0 && (
              <ul className="space-y-4">
                {actionableEvaluations.map((evaluation) => (
                  <RuleEvaluationRow key={evaluation.id} evaluation={evaluation} />
                ))}
              </ul>
            )}

            {quietEvaluations.length > 0 && (
              <details className="group">
                <summary className="cursor-pointer list-none rounded text-sm font-medium text-foreground-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring">
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
                <ul className="mt-4 space-y-4">
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
