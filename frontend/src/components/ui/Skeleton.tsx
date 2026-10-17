import { cn } from "@/lib/cn";
import { getI18n } from "@/lib/i18n/server";

/** Layout-stable placeholder block. Pulse is disabled for reduced-motion users. */
export function Skeleton({ className }: { className?: string }) {
  return (
    <div aria-hidden="true" className={cn("rounded bg-surface-muted motion-safe:animate-pulse", className)} />
  );
}

/** Placeholder with the same chrome as `DataTable`, so the page does not jump when data lands. */
export async function TableSkeleton({ rows = 6, columns = 4 }: { rows?: number; columns?: number }) {
  const { t } = await getI18n();
  return (
    <div
      role="status"
      aria-live="polite"
      className="overflow-hidden rounded-lg border border-border bg-surface"
    >
      <span className="sr-only">{t("common.loading")}</span>
      <div className="flex gap-6 border-b border-border bg-surface-muted px-3 py-2.5">
        {Array.from({ length: columns }).map((_, index) => (
          <Skeleton key={index} className="h-3 flex-1 bg-border" />
        ))}
      </div>
      {Array.from({ length: rows }).map((_, row) => (
        <div key={row} className="flex gap-6 border-b border-border px-3 py-3 last:border-b-0">
          {Array.from({ length: columns }).map((_, column) => (
            <Skeleton key={column} className={cn("h-3.5 flex-1", column === 0 && "max-w-56")} />
          ))}
        </div>
      ))}
    </div>
  );
}

/** Header + body skeleton for list and detail routes' `loading.tsx`. */
export function PageSkeleton({ children }: { children?: React.ReactNode }) {
  return (
    <div className="space-y-5">
      <div className="space-y-2 border-b border-border pb-4">
        <Skeleton className="h-7 w-56" />
        <Skeleton className="h-4 w-96 max-w-full" />
      </div>
      {children ?? <TableSkeleton />}
    </div>
  );
}
