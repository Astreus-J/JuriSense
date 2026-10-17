import { PageSkeleton, Skeleton } from "@/components/ui/Skeleton";
import { getI18n } from "@/lib/i18n/server";

export default async function Loading() {
  const { t } = await getI18n();
  return (
    <PageSkeleton>
      <div role="status" className="space-y-6">
        <span className="sr-only">{t("common.loading")}</span>
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-4 w-40" />
        <Skeleton className="h-32 w-full" />
      </div>
    </PageSkeleton>
  );
}
