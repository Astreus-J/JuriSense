"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { CheckCircle2 } from "lucide-react";

import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";

interface PublishVersionButtonProps {
  policyId: string;
  versionId: string;
}

/**
 * Publishing is a one-way freeze (BR-POL-001: every Rule in this version becomes
 * immutable; BR-POL-002: it becomes the Policy's one current version — there is no
 * un-publish, only a new draft version). Proportionate to that per persona "Destructive
 * actions", this uses a lightweight inline confirm step rather than a full modal dialog:
 * the button already lives in its own dedicated page section (not a dense list row where
 * an inline expansion would be cramped), so a modal's focus-trap/overlay machinery would
 * be over-designing a two-state toggle.
 */
export function PublishVersionButton({ policyId, versionId }: PublishVersionButtonProps) {
  const router = useRouter();
  const [confirming, setConfirming] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handlePublish() {
    setSubmitting(true);
    setError(null);
    try {
      const response = await fetch(`/api/policies/${policyId}/versions/${versionId}/publish`, {
        method: "POST",
      });
      if (!response.ok) {
        const body = (await response.json().catch(() => null)) as { detail?: string } | null;
        setError(body?.detail ?? "Could not publish this version.");
        setSubmitting(false);
        return;
      }
      router.refresh();
    } catch {
      setError("Could not reach the server. Try again.");
      setSubmitting(false);
    }
  }

  if (!confirming) {
    return (
      <div className="flex flex-col items-end gap-2">
        <Button onClick={() => setConfirming(true)}>
          <CheckCircle2 className="size-4" aria-hidden="true" />
          Publish version
        </Button>
        {error && (
          <Alert tone="danger" title="Could not publish" className="w-full max-w-sm">
            {error}
          </Alert>
        )}
      </div>
    );
  }

  return (
    <Alert tone="warning" title="Publish this version?" className="w-full max-w-sm">
      <div className="space-y-3">
        <p>
          Every rule in this version will be frozen permanently, and it becomes this
          policy&apos;s current version used for new compliance reviews. This can&apos;t be
          undone — further edits always require a new draft version.
        </p>
        {error && <p className="font-medium text-danger">{error}</p>}
        <div className="flex items-center gap-2">
          <Button variant="primary" onClick={handlePublish} loading={submitting}>
            Yes, publish
          </Button>
          <Button variant="ghost" onClick={() => setConfirming(false)} disabled={submitting}>
            Cancel
          </Button>
        </div>
      </div>
    </Alert>
  );
}
