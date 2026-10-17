import Link from "next/link";
import { SearchX } from "lucide-react";

import { buttonClasses } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { getI18n } from "@/lib/i18n/server";

/**
 * Rendered when `getDecisionPassport()` 404s in `[id]/page.tsx` (via `notFound()`) — a
 * missing Decision, one in another organization, and one with no EvidencePackage yet all
 * collapse to the same 404 (ADR-003), so this page doesn't distinguish them either.
 */
export default async function DecisionPassportNotFound() {
  const { t } = await getI18n();
  return (
    <EmptyState
      as="h1"
      icon={SearchX}
      title={t("decisions.notFoundTitle")}
      description={t("decisions.notFoundBody")}
      action={
        <Link href="/evidence" className={buttonClasses("secondary")}>
          {t("decisions.backToEvidence")}
        </Link>
      }
    />
  );
}
