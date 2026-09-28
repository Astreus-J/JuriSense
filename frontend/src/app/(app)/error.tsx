"use client";

import { useEffect } from "react";

import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";

/**
 * Segment error boundary for the whole authenticated app (Next 16 renamed
 * the recovery callback from `reset` to `unstable_retry` — see
 * `node_modules/next/dist/docs/01-app/03-api-reference/03-file-conventions/error.md`).
 * Never exposes the raw error to the user (persona: "Do not expose raw
 * backend exceptions").
 */
export default function AppError({
  error,
  unstable_retry,
}: {
  error: Error & { digest?: string };
  unstable_retry: () => void;
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
        <Button onClick={() => unstable_retry()}>Try again</Button>
      </div>
    </div>
  );
}
