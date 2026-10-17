import { DecisionMark } from "@/components/shared/StatusBadge";
import { EmptyState } from "@/components/ui/EmptyState";
import { formatDateTime } from "@/lib/format";
import { getI18n } from "@/lib/i18n/server";
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
export async function ComplianceReviewResults({ detail }: { detail: ComplianceReviewDetail }) {
  const { review, ruleEvaluations, risks } = detail;
  const { t, plural, locale } = await getI18n();

  const actionableEvaluations = ruleEvaluations.filter(
    (evaluation) => evaluation.outcome === "REVIEW" || evaluation.outcome === "BLOCK",
  );
  const quietEvaluations = ruleEvaluations.filter(
    (evaluation) => evaluation.outcome === "PASS" || evaluation.outcome === "NOT_APPLICABLE",
  );

  return (
    <div className="space-y-8">
      <section
        aria-label={t("compliance.results.decision")}
        className="flex flex-wrap items-center justify-between gap-x-8 gap-y-3 border-b border-border pb-5"
      >
        <DecisionMark value={review.status} caption={t("compliance.results.decision")} />
        <dl className="grid grid-cols-2 gap-x-8 gap-y-1 text-sm sm:grid-cols-3">
          <div>
            <dt className="text-xs text-foreground-muted">{t("compliance.results.started")}</dt>
            <dd className="tabular-nums">{formatDateTime(review.startedAt, locale)}</dd>
          </div>
          <div>
            <dt className="text-xs text-foreground-muted">{t("compliance.results.completed")}</dt>
            <dd className="tabular-nums">
              {review.completedAt
                ? formatDateTime(review.completedAt, locale)
                : t("compliance.results.notCompleted")}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-foreground-muted">{t("compliance.results.policyCoverage")}</dt>
            <dd className="tabular-nums">
              {plural("compliance.results.publishedVersions", review.policyVersionIds.length)}
            </dd>
          </div>
        </dl>
      </section>

      <section className="space-y-3">
        <h2 className="text-base font-semibold text-foreground">{t("compliance.results.risks")}</h2>

        {risks.length === 0 ? (
          <EmptyState
            title={
              review.status === "APPROVE"
                ? t("compliance.results.noRisksFound")
                : t("compliance.results.noRisksRecorded")
            }
            description={
              review.status === "APPROVE"
                ? t("compliance.results.allPassed")
                : t("compliance.results.noRisksBody")
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
          {t("compliance.results.evaluatedRules")} <span className="font-normal tabular-nums text-foreground-muted">({ruleEvaluations.length})</span>
        </h2>

        {ruleEvaluations.length === 0 ? (
          <EmptyState
            title={t("compliance.results.noRulesTitle")}
            description={
              review.policyVersionIds.length === 0
                ? t("compliance.results.noRulesNoPolicy")
                : t("compliance.results.noRulesEmpty")
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
                    {t("compliance.results.showMore", { count: quietEvaluations.length })}
                  </span>
                  <span className="hidden group-open:inline">
                    {t("compliance.results.hideQuiet")}
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
