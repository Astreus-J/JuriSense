import Link from "next/link";
import { SearchX } from "lucide-react";

import { buttonClasses } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { getI18n } from "@/lib/i18n/server";

/**
 * Rendered when the policy or the policy version 404s in this segment's `page.tsx` (via
 * `notFound()`) — matching `policies/[id]/not-found.tsx`'s identical reasoning for not
 * distinguishing "no such policy" from "no such version" from "wrong organization".
 */
export default async function PolicyVersionNotFound() {
  const { t } = await getI18n();
  return (
    <EmptyState
      as="h1"
      icon={SearchX}
      title={t("policies.version.notFoundTitle")}
      description={t("policies.version.notFoundBody")}
      action={
        <Link href="/policies" className={buttonClasses("secondary")}>
          {t("policies.detail.backToList")}
        </Link>
      }
    />
  );
}
