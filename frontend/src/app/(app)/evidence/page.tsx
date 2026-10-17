import Link from "next/link";
import { ExternalLink } from "lucide-react";

import { PageHeader } from "@/components/ui/PageHeader";
import { DecisionLookupForm } from "@/components/evidence/DecisionLookupForm";
import { getI18n, pageTitle } from "@/lib/i18n/server";

export const generateMetadata = pageTitle("meta.evidence");

/**
 * STORY-7.3.1: the Decision Passport's one entry point from the nav shell. A full
 * audit-trail browser (`NAV_ITEMS.evidence`'s longer-term description) is out of this
 * story's scope — only the Decision Passport lookup ships here.
 *
 * STORY-8.3.1: also links to `/verify`, the public, unauthenticated verification page --
 * reachable without a session on its own, but surfaced here too so a signed-in user can grab
 * its shareable link (e.g. to hand to an external auditor) without leaving the app.
 */
export default async function EvidencePage() {
  const { t } = await getI18n();
  return (
    <div className="space-y-6">
      <PageHeader
        title={t("nav.evidence")}
        description={t("evidence.description")}
      />
      <section aria-labelledby="decision-lookup-title" className="max-w-2xl space-y-3">
        <h2 id="decision-lookup-title" className="text-base font-semibold text-foreground">
          {t("evidence.lookupTitle")}
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
          {t("evidence.openVerify")}
        </Link>
        <span className="ml-2 text-sm text-foreground-muted">
          {t("evidence.verifyNote")}
        </span>
      </p>
    </div>
  );
}
