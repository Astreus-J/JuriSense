import Link from "next/link";

import { Brand } from "@/components/app-shell/Brand";
import { getI18n } from "@/lib/i18n/server";

export default async function NotFound() {
  const { t } = await getI18n();
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-6 bg-surface-muted px-4 text-center">
      <Brand />
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold text-foreground">{t("errors.pageNotFound")}</h1>
        <p className="text-sm text-foreground-muted">
          {t("errors.pageNotFoundDescription")}
        </p>
      </div>
      <Link
        href="/dashboard"
        className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring focus-visible:ring-offset-2"
      >
        {t("common.backToDashboard")}
      </Link>
    </div>
  );
}
