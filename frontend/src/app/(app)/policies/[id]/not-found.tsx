import Link from "next/link";
import { SearchX } from "lucide-react";

import { buttonClasses } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { getI18n } from "@/lib/i18n/server";

/**
 * Rendered when `getPolicy()` 404s in `[id]/page.tsx` (via `notFound()`) — either the
 * policy doesn't exist, or it belongs to a different organization (the API returns the
 * same 404 for both, so this page doesn't distinguish them either, matching
 * `suppliers/[id]/not-found.tsx`'s identical reasoning — doing so would leak cross-tenant
 * existence).
 */
export default async function PolicyNotFound() {
  const { t } = await getI18n();
  return (
    <EmptyState
      as="h1"
      icon={SearchX}
      title={t("policies.detail.notFoundTitle")}
      description={t("policies.detail.notFoundBody")}
      action={
        <Link href="/policies" className={buttonClasses("secondary")}>
          {t("policies.detail.backToList")}
        </Link>
      }
    />
  );
}
