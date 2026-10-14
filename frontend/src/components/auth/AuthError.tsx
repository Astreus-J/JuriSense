"use client";

import { useEffect } from "react";

import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { AuthShell } from "./AuthShell";

/**
 * #130/#136: shared body for `src/app/login/error.tsx` and
 * `src/app/invite/accept/error.tsx` -- these two public pages call `getSession()`
 * (to redirect an already-authenticated visitor away) with no boundary above them
 * before this, so a 5xx/network failure there fell through to Next's default error
 * screen instead of this app's own error UI, unlike every page inside `(app)/`.
 * Mirrors `(app)/error.tsx`'s contract (never expose the raw error) in the
 * `AuthShell` card layout these two pages already use instead of the
 * dashboard-oriented one. Code review (2026-10-14): the installed Next.js
 * (16.4.0) error boundary passes `retry`, not `unstable_retry` (that was only
 * the transitional name in 16.2.0, stable as `retry` since 16.3.0 --
 * `node_modules/next/dist/client/components/error-boundary.js` calls
 * `errorComponent({ error, reset, retry })`); the wrong name silently made
 * the one recovery button on this screen throw instead of retrying.
 */
export function AuthError({
  error,
  retry,
}: {
  error: Error & { digest?: string };
  retry: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <AuthShell heading="Something went wrong">
      <div className="space-y-4">
        <Alert tone="danger" title="This page ran into an unexpected error.">
          You can try again, or come back later.
        </Alert>
        <Button onClick={() => retry()}>Try again</Button>
      </div>
    </AuthShell>
  );
}
