import Link from "next/link";
import { SearchX } from "lucide-react";

import { buttonClasses } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { getI18n } from "@/lib/i18n/server";

/**
 * Rendered when `getSupplier()` 404s in `[id]/page.tsx` (via `notFound()`) — either the
 * supplier doesn't exist, or it belongs to a different organization (the API returns the
 * same 404 for both, so this page doesn't distinguish them either — doing so would leak
 * cross-tenant existence).
 */
export default async function SupplierNotFound() {
  const { t } = await getI18n();
  return (
    <EmptyState
      as="h1"
      icon={SearchX}
      title={t("suppliers.detail.notFoundTitle")}
      description={t("suppliers.detail.notFoundBody")}
      action={
        <Link href="/suppliers" className={buttonClasses("secondary")}>
          {t("suppliers.detail.backToList")}
        </Link>
      }
    />
  );
}
