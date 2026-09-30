import { Badge } from "@/components/ui/Badge";
import { formatConfidence } from "@/lib/format";
import type { Clause } from "@/lib/contracts/types";

function formatClauseType(clauseType: string): string {
  return clauseType.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());
}

/** CON-004/BR-CON-004: every clause carries its page/span citation — the direct evidence a
 * `RuleEvaluation` will later cite (persona: "Evidence should be directly connected to
 * conclusions"). Rendered as a flat list rather than grouped by `clause_type` to keep page
 * order scannable, since that's how a reviewer would cross-check against the document. */
export function ClauseList({ clauses }: { clauses: Clause[] }) {
  return (
    <section className="space-y-3">
      <h2 className="text-sm font-semibold text-foreground">Clauses</h2>

      {clauses.length === 0 ? (
        <p className="rounded-xl border border-dashed border-border bg-surface px-6 py-10 text-center text-sm text-foreground-muted">
          No clauses were identified in this version.
        </p>
      ) : (
        <ul className="space-y-2">
          {clauses.map((clause) => (
            <li key={clause.id} className="rounded-xl border border-border bg-surface p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge tone="neutral">{formatClauseType(clause.clauseType)}</Badge>
                  <span className="text-xs text-foreground-muted">Page {clause.page}</span>
                </div>
                <span className="text-xs font-medium text-foreground-muted">
                  {formatConfidence(clause.confidence)} confidence
                </span>
              </div>
              {clause.textExcerpt && (
                <p className="mt-2 text-sm text-foreground-muted">&ldquo;{clause.textExcerpt}&rdquo;</p>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
