"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Plus } from "lucide-react";

import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { useI18n } from "@/lib/i18n/client";

interface CreateDraftVersionButtonProps {
  policyId: string;
}

/**
 * BR-POL-001's "editing always produces a new version" entry point. No confirmation step
 * — unlike publishing, creating a draft is reversible in effect (an unused draft is
 * harmless) and additive, so a lightweight one-click action is proportionate (persona:
 * "do not over-design"). Navigates straight to the new draft so the reviewer can start
 * adding/editing rules immediately, mirroring `TriggerComplianceReviewButton`'s
 * navigate-to-the-new-thing pattern.
 */
export function CreateDraftVersionButton({ policyId }: CreateDraftVersionButtonProps) {
  const router = useRouter();
  const { t } = useI18n();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleClick() {
    setSubmitting(true);
    setError(null);
    try {
      const response = await fetch(`/api/policies/${policyId}/versions`, { method: "POST" });
      if (!response.ok) {
        const body = (await response.json().catch(() => null)) as { detail?: string } | null;
        setError(body?.detail ?? t("policies.newDraft.failedDefault"));
        setSubmitting(false);
        return;
      }
      const version = (await response.json()) as { id: string };
      router.push(`/policies/${policyId}/versions/${version.id}`);
      router.refresh();
    } catch {
      setError(t("errors.unreachableRetry"));
      setSubmitting(false);
    }
  }

  return (
    <div className="flex flex-col items-end gap-2">
      <Button variant="secondary" onClick={handleClick} loading={submitting}>
        <Plus className="size-4" aria-hidden="true" />
        {t("policies.newDraft.button")}
      </Button>
      {error && (
        <Alert tone="danger" title={t("policies.newDraft.errorTitle")} className="w-full max-w-sm">
          {error}
        </Alert>
      )}
    </div>
  );
}
