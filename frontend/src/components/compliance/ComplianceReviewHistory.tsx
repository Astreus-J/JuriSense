import Link from "next/link";

import { formatDateTime } from "@/lib/format";
import type { ComplianceReview } from "@/lib/compliance/types";
import { ComplianceStatusBadge } from "./ComplianceStatusBadge";

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
    <section className="space-y-2 rounded-xl border border-border bg-surface p-4">
      <h2 className="text-xs font-semibold uppercase tracking-wide text-foreground-muted">
        Compliance review history
      </h2>
      <ul className="divide-y divide-border">
        {newestFirst.map((review) => (
          <li key={review.id}>
            <Link
              href={`/compliance/reviews/${review.id}?contractId=${contractId}`}
              className="flex flex-wrap items-center justify-between gap-2 py-2 text-sm hover:underline"
            >
              <ComplianceStatusBadge status={review.status} />
              <span className="text-foreground-muted">{formatDateTime(review.startedAt)}</span>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
