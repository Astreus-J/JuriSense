import type { Metadata } from "next";
import Link from "next/link";
import { ExternalLink } from "lucide-react";

import { PageHeader } from "@/components/ui/PageHeader";
import { DecisionLookupForm } from "@/components/evidence/DecisionLookupForm";

export const metadata: Metadata = { title: "Evidence & Audit — JuriSense Gate" };

/**
 * STORY-7.3.1: the Decision Passport's one entry point from the nav shell. A full
 * audit-trail browser (`NAV_ITEMS.evidence`'s longer-term description) is out of this
 * story's scope — only the Decision Passport lookup ships here.
 *
 * STORY-8.3.1: also links to `/verify`, the public, unauthenticated verification page --
 * reachable without a session on its own, but surfaced here too so a signed-in user can grab
 * its shareable link (e.g. to hand to an external auditor) without leaving the app.
 */
export default function EvidencePage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Evidence & Audit"
        description='Look up the complete, reproducible "why was this approved?" record for any decision.'
      />
      <section aria-labelledby="decision-lookup-title" className="max-w-2xl space-y-3">
        <h2 id="decision-lookup-title" className="text-base font-semibold text-foreground">
          Find a Decision Passport
        </h2>
        <DecisionLookupForm />
      </section>
      <p className="border-t border-border pt-4">
        <Link
          href="/verify"
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1.5 text-sm font-medium text-primary hover:underline"
        >
          <ExternalLink className="size-4" aria-hidden="true" />
          Open the public verification page
        </Link>
        <span className="ml-2 text-sm text-foreground-muted">
          No login required; shareable with external auditors.
        </span>
      </p>
    </div>
  );
}
