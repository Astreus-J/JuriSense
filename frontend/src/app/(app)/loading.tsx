/**
 * Shown immediately while `(app)/layout.tsx` awaits `requireSession()`
 * (the `/auth/me` round-trip). Mirrors the shell's actual layout so there is
 * no jarring blank-to-full-UI flash (persona: "preserve layout stability").
 */
export default function AuthenticatedLoading() {
  return (
    <div className="flex h-screen overflow-hidden bg-surface-muted">
      <aside className="hidden w-64 shrink-0 flex-col gap-4 border-r border-border bg-surface px-4 py-5 md:flex">
        <div className="h-6 w-32 animate-pulse rounded bg-surface-muted" />
        <div className="h-9 w-full animate-pulse rounded-md bg-surface-muted" />
        <div className="space-y-2 pt-2">
          {Array.from({ length: 5 }).map((_, index) => (
            <div key={index} className="h-8 w-full animate-pulse rounded-md bg-surface-muted" />
          ))}
        </div>
      </aside>
      <div className="flex flex-1 flex-col overflow-hidden">
        <header className="flex h-14 shrink-0 items-center justify-end border-b border-border bg-surface px-4 md:px-6">
          <div className="size-7 animate-pulse rounded-full bg-surface-muted" />
        </header>
        <main className="flex-1 p-4 md:p-8">
          <div className="mx-auto max-w-5xl space-y-4">
            <div className="h-7 w-64 animate-pulse rounded bg-surface" />
            <div className="h-4 w-96 max-w-full animate-pulse rounded bg-surface" />
          </div>
        </main>
      </div>
    </div>
  );
}
