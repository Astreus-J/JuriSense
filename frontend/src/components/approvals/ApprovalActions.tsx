"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Textarea } from "@/components/ui/Textarea";

interface ApprovalActionsProps {
  requestId: string;
}

type PendingAction = "approve" | "reject" | null;
type ActionError = { action: "approve" | "reject"; message: string } | null;

/**
 * Approve/Reject for a single `ApprovalRequest`, mirroring `SupplierDetailActions.tsx`'s
 * mutating-action pattern exactly: `"use client"`, local loading/error state, a POST to a
 * BFF Route Handler, `router.refresh()` on success. There is no local "resolved" state to
 * manage here beyond that: `router.refresh()` re-runs `/approvals/page.tsx`'s server-side
 * fetch of `GET /approvals/requests/pending`, which simply no longer includes this request
 * once it's `approved`/`rejected` — the row disappears because the data says so, not
 * because this component hides it optimistically.
 *
 * Justification is optional on approve, mandatory on reject (BR-APR-002) — enforced
 * server-side (`EmptyJustificationError`), not by disabling the Reject button client-side,
 * so a 422 with the backend's real message ("A non-empty justification is required") is
 * always what a user seeing this button sees, never a generic fallback.
 */
export function ApprovalActions({ requestId }: ApprovalActionsProps) {
  const router = useRouter();
  const [justification, setJustification] = useState("");
  const [pending, setPending] = useState<PendingAction>(null);
  const [error, setError] = useState<ActionError>(null);

  async function resolve(action: "approve" | "reject") {
    setPending(action);
    setError(null);
    try {
      const response = await fetch(`/api/approvals/requests/${requestId}/${action}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ justification }),
      });
      if (!response.ok) {
        const body = (await response.json().catch(() => null)) as { detail?: string } | null;
        setError({
          action,
          message: body?.detail ?? `Could not ${action} this request. Try again.`,
        });
        return;
      }
      router.refresh();
    } catch {
      setError({ action, message: "Could not reach the server. Try again." });
    } finally {
      setPending(null);
    }
  }

  const isBusy = pending !== null;

  return (
    <div className="space-y-3 border-t border-border pt-3">
      <Textarea
        label="Justification"
        hint="Optional to approve. Required to reject."
        value={justification}
        onChange={(event) => setJustification(event.target.value)}
        disabled={isBusy}
        rows={2}
      />

      <div className="flex flex-wrap items-center justify-end gap-2">
        <Button
          type="button"
          variant="danger"
          onClick={() => resolve("reject")}
          loading={pending === "reject"}
          disabled={isBusy}
        >
          Reject
        </Button>
        <Button
          type="button"
          variant="primary"
          onClick={() => resolve("approve")}
          loading={pending === "approve"}
          disabled={isBusy}
        >
          Approve
        </Button>
      </div>

      {error && (
        <Alert
          tone="danger"
          title={
            error.action === "reject" ? "Could not reject this request" : "Could not approve this request"
          }
        >
          {error.message}
        </Alert>
      )}
    </div>
  );
}
