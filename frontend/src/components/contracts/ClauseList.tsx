import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
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
      <h2 className="text-base font-semibold text-foreground">Clauses</h2>

      {clauses.length === 0 ? (
        <EmptyState
          title="No clauses identified"
          description="No clauses were identified in this version."
        />
      ) : (
        <ul className="divide-y divide-border border-y border-border">
          {clauses.map((clause) => (
            <li key={clause.id} className="py-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge tone="neutral">{formatClauseType(clause.clauseType)}</Badge>
                  <span className="text-xs tabular-nums text-foreground-muted">Page {clause.page}</span>
                </div>
                <span className="text-xs tabular-nums text-foreground-muted">
                  {formatConfidence(clause.confidence)} confidence
                </span>
              </div>
              {clause.textExcerpt && (
                <p className="mt-1.5 border-l-2 border-border-strong pl-3 text-sm text-foreground-muted">
                  {clause.textExcerpt}
                </p>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
