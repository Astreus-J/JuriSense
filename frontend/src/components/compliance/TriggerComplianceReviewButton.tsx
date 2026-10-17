"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";

interface TriggerComplianceReviewButtonProps {
  contractId: string;
  contractVersionId: string;
}

/**
 * #62's entry point: starts a real, synchronous `ComplianceReview` for the currently-selected
 * `ContractVersion` and navigates straight to its results screen — unlike
 * `SupplierDetailActions`'s re-check button, there is no "stay on this page and refresh" case
 * here, since the whole point is to land on the new review's WHY/EVIDENCE/POLICY/SOURCE
 * breakdown. Only rendered by the caller when `permissions.canCreate` is true and the
 * contract version is `analyzed` — this component doesn't re-check either, by this
 * codebase's convention (`SupplierDetailActions`'s own docstring: "renders nothing rather
 * than a disabled control", the real check is server-side).
 */
export function TriggerComplianceReviewButton({
  contractId,
  contractVersionId,
}: TriggerComplianceReviewButtonProps) {
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleClick() {
    setSubmitting(true);
    setError(null);
    try {
      const response = await fetch("/api/compliance/reviews", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ contractVersionId }),
      });

      if (!response.ok) {
        const body = (await response.json().catch(() => null)) as { detail?: string } | null;
        setError(body?.detail ?? "Could not start a compliance review.");
        setSubmitting(false);
        return;
      }

      const review = (await response.json()) as { id: string };
      router.push(`/compliance/reviews/${review.id}?contractId=${contractId}`);
    } catch {
      setError("Could not reach the server. Try again.");
      setSubmitting(false);
    }
  }

  return (
    <div className="flex flex-col items-end gap-2">
      <Button variant="primary" onClick={handleClick} loading={submitting}>
        Run compliance review
      </Button>

      {error && (
        <Alert tone="danger" title="Could not start review" className="w-full max-w-sm">
          {error}
        </Alert>
      )}
    </div>
  );
}
