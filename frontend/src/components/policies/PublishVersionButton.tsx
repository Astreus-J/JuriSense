"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { CheckCircle2 } from "lucide-react";

import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { useI18n } from "@/lib/i18n/client";

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
  const { t } = useI18n();
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
        setError(body?.detail ?? t("policies.publish.failedDefault"));
        setSubmitting(false);
        return;
      }
      router.refresh();
    } catch {
      setError(t("errors.unreachableRetry"));
      setSubmitting(false);
    }
  }

  if (!confirming) {
    return (
      <div className="flex flex-col items-end gap-2">
        <Button onClick={() => setConfirming(true)}>
          <CheckCircle2 className="size-4" aria-hidden="true" />
          {t("policies.publish.button")}
        </Button>
        {error && (
          <Alert tone="danger" title={t("policies.publish.errorTitle")} className="w-full max-w-sm">
            {error}
          </Alert>
        )}
      </div>
    );
  }

  return (
    <Alert tone="warning" title={t("policies.publish.confirmTitle")} className="w-full max-w-sm">
      <div className="space-y-3">
        <p>
          {t("policies.publish.confirmBody")}
        </p>
        {error && <p className="font-medium text-danger">{error}</p>}
        <div className="flex items-center gap-2">
          <Button variant="primary" onClick={handlePublish} loading={submitting}>
            {t("policies.publish.confirmYes")}
          </Button>
          <Button variant="ghost" onClick={() => setConfirming(false)} disabled={submitting}>
            {t("common.cancel")}
          </Button>
        </div>
      </div>
    </Alert>
  );
}
