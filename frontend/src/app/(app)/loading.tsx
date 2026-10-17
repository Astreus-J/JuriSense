import { Skeleton } from "@/components/ui/Skeleton";
import { getI18n } from "@/lib/i18n/server";

/**
 * Shown immediately while `(app)/layout.tsx` awaits `requireSession()`
 * (the `/auth/me` round-trip). Mirrors the shell's actual layout (sidebar width, top bar
 * height, content width) so there is no jarring blank-to-full-UI flash.
 */
export default async function AuthenticatedLoading() {
  const { t } = await getI18n();
  return (
    <div className="flex h-screen overflow-hidden bg-surface" role="status">
      <span className="sr-only">{t("common.loading")}</span>
      <aside className="hidden w-56 shrink-0 flex-col border-r border-border bg-surface-muted md:flex">
        <div className="flex h-14 items-center border-b border-border px-4">
          <Skeleton className="h-5 w-32 bg-border" />
        </div>
        <div className="space-y-2 px-3 py-4">
          <Skeleton className="h-10 w-full bg-border" />
          {Array.from({ length: 5 }).map((_, index) => (
            <Skeleton key={index} className="h-7 w-full bg-border" />
          ))}
        </div>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <header className="flex h-14 shrink-0 items-center justify-end border-b border-border px-4 md:px-6">
          <Skeleton className="size-7" />
        </header>
        <main className="flex-1 overflow-hidden">
          <div className="mx-auto w-full max-w-6xl space-y-3 px-4 py-6 md:px-8 md:py-8">
            <Skeleton className="h-7 w-64" />
            <Skeleton className="h-4 w-96 max-w-full" />
          </div>
        </main>
      </div>
    </div>
  );
}
