import Link from "next/link";
import { SearchX } from "lucide-react";

import { buttonClasses } from "@/components/ui/Button";

/**
 * Rendered when `getDecisionPassport()` 404s in `[id]/page.tsx` (via `notFound()`) — a
 * missing Decision, one in another organization, and one with no EvidencePackage yet all
 * collapse to the same 404 (ADR-003), so this page doesn't distinguish them either.
 */
export default function DecisionPassportNotFound() {
  return (
    <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-border bg-surface px-6 py-16 text-center">
      <div className="flex size-12 items-center justify-center rounded-full bg-surface-muted">
        <SearchX className="size-6 text-foreground-muted" aria-hidden="true" />
      </div>
      <h1 className="text-lg font-semibold text-foreground">Decision not found</h1>
      <p className="max-w-sm text-sm text-foreground-muted">
        This decision doesn&apos;t exist, isn&apos;t part of your organization, or has no evidence
        package yet.
      </p>
      <Link href="/evidence" className={buttonClasses("secondary", "mt-1")}>
        Back to Evidence & Audit
      </Link>
    </div>
  );
}
