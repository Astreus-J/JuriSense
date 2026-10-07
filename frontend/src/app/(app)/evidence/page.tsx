import type { Metadata } from "next";

import { DecisionLookupForm } from "@/components/evidence/DecisionLookupForm";

export const metadata: Metadata = { title: "Evidence & Audit — JuriSense Gate" };

/**
 * STORY-7.3.1: the Decision Passport's one entry point from the nav shell. A full
 * audit-trail browser (`NAV_ITEMS.evidence`'s longer-term description) is out of this
 * story's scope — only the Decision Passport lookup ships here.
 */
export default function EvidencePage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Evidence & Audit</h1>
        <p className="mt-1 text-sm text-foreground-muted">
          Look up the complete, reproducible &quot;why was this approved?&quot; record for any
          decision.
        </p>
      </div>
      <div className="rounded-xl border border-border bg-surface p-6">
        <DecisionLookupForm />
      </div>
    </div>
  );
}
