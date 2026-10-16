import { StatusBadge } from "@/components/shared/StatusBadge";
import Link from "next/link";

import { formatDateTime } from "@/lib/format";
import type { ComplianceReview } from "@/lib/compliance/types";

interface ComplianceReviewHistoryProps {
  contractId: string;
  /** Oldest-first, matching `listComplianceReviews`'s API order — reversed here for display. */
  reviews: ComplianceReview[];
}

/**
 * #62: a compact, newest-first list of past `ComplianceReview`s for the currently-selected
 * `ContractVersion`, each linking straight to its full results screen. The caller only
 * renders this when `reviews` is non-empty — the "Run compliance review" button above already
 * communicates the "not reviewed yet" state, so an explicit empty state here would just be
 * clutter (persona: "don't clutter the page when there's simply nothing yet").
 */
export function ComplianceReviewHistory({ contractId, reviews }: ComplianceReviewHistoryProps) {
  const newestFirst = [...reviews].reverse();

  return (
    <section className="space-y-1">
      <h2 className="text-base font-semibold text-foreground">Compliance reviews</h2>
      <ul className="divide-y divide-border border-y border-border">
        {newestFirst.map((review) => (
          <li key={review.id}>
            <Link
              href={`/compliance/reviews/${review.id}?contractId=${contractId}`}
              className="flex flex-wrap items-center justify-between gap-2 py-2 text-sm hover:bg-surface-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-focus-ring"
            >
              <StatusBadge kind="decision" value={review.status} />
              <span className="tabular-nums text-foreground-muted">{formatDateTime(review.startedAt)}</span>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
