"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { Textarea } from "@/components/ui/Textarea";

interface ApprovalActionsProps {
  requestId: string;
}

type PendingAction = "approve" | "reject" | null;
type ActionError = { action: "approve" | "reject"; message: string } | null;

/**
 * Approve/Reject for a single `ApprovalRequest`, mirroring `SupplierDetailActions.tsx`'s
 * mutating-action pattern: `"use client"`, local loading/error state, a POST to a BFF Route
 * Handler, `router.refresh()` on success. There is no local "resolved" state to manage
 * beyond that: `router.refresh()` re-runs `/approvals/page.tsx`'s server-side fetch of
 * `GET /approvals/requests/pending`, which simply no longer includes this request once it's
 * `approved`/`rejected`.
 *
 * Justification is optional on approve, mandatory on reject (BR-APR-002). The Reject button
 * is disabled until the justification is non-empty so the user gets the rule up front; the
 * server check (`EmptyJustificationError`) remains authoritative and its message is still
 * surfaced verbatim if it ever fires. Both outcomes are decisive and recorded in the audit
 * trail, so each goes through a native <dialog> confirmation that restates the consequence.
 */
export function ApprovalActions({ requestId }: ApprovalActionsProps) {
  const router = useRouter();
  const [justification, setJustification] = useState("");
  const [pending, setPending] = useState<PendingAction>(null);
  const [confirming, setConfirming] = useState<"approve" | "reject" | null>(null);
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
      setConfirming(null);
    }
  }

  const isBusy = pending !== null;
  const hasJustification = justification.trim().length > 0;

  return (
    <div className="space-y-3">
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
          variant="secondary"
          onClick={() => setConfirming("reject")}
          disabled={isBusy || !hasJustification}
          title={hasJustification ? undefined : "Enter a justification to reject"}
        >
          Reject
        </Button>
        <Button
          type="button"
          variant="primary"
          onClick={() => setConfirming("approve")}
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

      <ConfirmDialog
        open={confirming === "reject"}
        title="Reject this request?"
        tone="danger"
        confirmLabel="Reject request"
        loading={pending === "reject"}
        onCancel={() => setConfirming(null)}
        onConfirm={() => resolve("reject")}
      >
        <p>
          The request is closed as rejected and your justification is recorded in the audit
          trail. This cannot be undone.
        </p>
        <blockquote className="mt-2 border-l-2 border-border-strong pl-3 text-foreground">
          {justification.trim()}
        </blockquote>
      </ConfirmDialog>

      <ConfirmDialog
        open={confirming === "approve"}
        title="Approve this request?"
        confirmLabel="Approve request"
        loading={pending === "approve"}
        onCancel={() => setConfirming(null)}
        onConfirm={() => resolve("approve")}
      >
        <p>
          Your approval is recorded in the audit trail and the review moves to its next step.
          This cannot be undone.
        </p>
        {hasJustification && (
          <blockquote className="mt-2 border-l-2 border-border-strong pl-3 text-foreground">
            {justification.trim()}
          </blockquote>
        )}
      </ConfirmDialog>
    </div>
  );
}
