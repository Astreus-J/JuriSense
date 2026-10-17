import { PageSkeleton, Skeleton } from "@/components/ui/Skeleton";
import { getI18n } from "@/lib/i18n/server";

export default async function Loading() {
  const { t } = await getI18n();
  return (
    <PageSkeleton>
      <div role="status" className="divide-y divide-border border-y border-border">
        <span className="sr-only">{t("approvals.loading")}</span>
        {Array.from({ length: 3 }).map((_, index) => (
          <div key={index} className="grid gap-4 py-4 md:grid-cols-[1fr_22rem]">
            <div className="space-y-2">
              <Skeleton className="h-4 w-40" />
              <Skeleton className="h-3.5 w-56" />
              <Skeleton className="h-3.5 w-48" />
            </div>
            <Skeleton className="h-20 w-full" />
          </div>
        ))}
      </div>
    </PageSkeleton>
  );
}
