import Link from "next/link";
import { SearchX } from "lucide-react";

import { buttonClasses } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { getI18n } from "@/lib/i18n/server";

/**
 * Rendered when `getContract()` 404s in `[id]/page.tsx` (via `notFound()`) — either the
 * contract doesn't exist, or it belongs to a different organization (the API returns the
 * same 404 for both, so this page doesn't distinguish them either — doing so would leak
 * cross-tenant existence, same rationale as `suppliers/[id]/not-found.tsx`).
 */
export default async function ContractNotFound() {
  const { t } = await getI18n();
  return (
    <EmptyState
      as="h1"
      icon={SearchX}
      title={t("contracts.detail.notFoundTitle")}
      description={t("contracts.detail.notFoundBody")}
      action={
        <Link href="/contracts" className={buttonClasses("secondary")}>
          {t("contracts.detail.backToList")}
        </Link>
      }
    />
  );
}
