"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { Textarea } from "@/components/ui/Textarea";
import { useI18n } from "@/lib/i18n/client";

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
  const { t } = useI18n();
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
          message:
            body?.detail ??
            (action === "approve"
              ? t("approvals.actions.approveFailedDefault")
              : t("approvals.actions.rejectFailedDefault")),
        });
        return;
      }
      router.refresh();
    } catch {
      setError({ action, message: t("errors.unreachableRetry") });
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
        label={t("approvals.actions.justification")}
        hint={t("approvals.actions.justificationHint")}
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
          title={hasJustification ? undefined : t("approvals.actions.rejectNeedsJustification")}
        >
          {t("approvals.actions.reject")}
        </Button>
        <Button
          type="button"
          variant="primary"
          onClick={() => setConfirming("approve")}
          disabled={isBusy}
        >
          {t("approvals.actions.approve")}
        </Button>
      </div>

      {error && (
        <Alert
          tone="danger"
          title={
            error.action === "reject"
              ? t("approvals.actions.couldNotReject")
              : t("approvals.actions.couldNotApprove")
          }
        >
          {error.message}
        </Alert>
      )}

      <ConfirmDialog
        open={confirming === "reject"}
        title={t("approvals.actions.rejectConfirmTitle")}
        tone="danger"
        confirmLabel={t("approvals.actions.rejectConfirmLabel")}
        loading={pending === "reject"}
        onCancel={() => setConfirming(null)}
        onConfirm={() => resolve("reject")}
      >
        <p>{t("approvals.actions.rejectConfirmBody")}</p>
        <blockquote className="mt-2 border-l-2 border-border-strong pl-3 text-foreground">
          {justification.trim()}
        </blockquote>
      </ConfirmDialog>

      <ConfirmDialog
        open={confirming === "approve"}
        title={t("approvals.actions.approveConfirmTitle")}
        confirmLabel={t("approvals.actions.approveConfirmLabel")}
        loading={pending === "approve"}
        onCancel={() => setConfirming(null)}
        onConfirm={() => resolve("approve")}
      >
        <p>{t("approvals.actions.approveConfirmBody")}</p>
        {hasJustification && (
          <blockquote className="mt-2 border-l-2 border-border-strong pl-3 text-foreground">
            {justification.trim()}
          </blockquote>
        )}
      </ConfirmDialog>
    </div>
  );
}
