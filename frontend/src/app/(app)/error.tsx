"use client";

import { useEffect } from "react";

import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";

/**
 * Segment error boundary for the whole authenticated app. Never exposes the
 * raw error to the user (persona: "Do not expose raw backend exceptions").
 *
 * Code review (2026-10-14): the installed Next.js (16.4.0) error boundary
 * passes `retry`, not `unstable_retry` -- that was only the transitional
 * name in 16.2.0, stable as `retry` since 16.3.0
 * (`node_modules/next/dist/client/components/error-boundary.js` calls
 * `errorComponent({ error, reset, retry })`;
 * `node_modules/next/dist/docs/.../error.md`'s own version table confirms
 * the same). The wrong prop name meant the one "Try again" button on every
 * authenticated page's error screen silently threw instead of retrying.
 */
export default function AppError({
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
    <div className="flex min-h-[60vh] items-center justify-center p-6">
      <div className="w-full max-w-md space-y-4">
        <Alert tone="danger" title="Something went wrong.">
          This page ran into an unexpected error. You can try again, or come back later.
        </Alert>
        <Button onClick={() => retry()}>Try again</Button>
      </div>
    </div>
  );
}
