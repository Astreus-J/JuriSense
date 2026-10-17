"use client";

import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { useRouter } from "next/navigation";

import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { controlClasses } from "@/components/ui/Field";
import { useI18n } from "@/lib/i18n/client";
import { ALLOWED_STATUS_TRANSITIONS } from "@/lib/suppliers/types";
import type { Supplier, SupplierCheck, SupplierStatus } from "@/lib/suppliers/types";

interface SupplierDetailActionsProps {
  supplier: Supplier;
  canUpdate: boolean;
}

// `recheck` = the start request itself failed (never got a 202); `recheck_failed` = it
// started fine but the async Celery task later settled as `failed` -- code review
// (2026-10-14): these were conflated under one title ("Could not start check"), which
// is actively wrong for the second case (it DID start; it failed afterward).
type ActionError =
  | { action: "recheck" | "recheck_failed" | "status"; message: string }
  | null;

// #142: the 202 from POST .../recheck only confirms the Celery task *started* -- not
// how it turns out. Poll a few times for a reasonable window, then give up quietly
// (best-effort, same spirit as this app's other "don't block the UI on an async
// settle" spots) rather than polling forever if something's genuinely stuck.
const RECHECK_POLL_INTERVAL_MS = 3000;
const RECHECK_POLL_MAX_ATTEMPTS = 20; // ~60s

/**
 * Manual re-check (SUP-002) and status-change (BR-SUP-003) actions. Both require the
 * `suppliers:update` permission — `canUpdate` is a UI hint from the caller
 * (`getSupplierPermissions`, a default-role-grid mirror), but the component still renders
 * nothing rather than a disabled control when the hint says no, and the real permission
 * check happens server-side on every submit regardless (see the Route Handlers this posts
 * to) — a 403 here is a normal, handled error state, not a crash.
 */
export function SupplierDetailActions({ supplier, canUpdate }: SupplierDetailActionsProps) {
  const router = useRouter();
  const { t } = useI18n();
  const [rechecking, setRechecking] = useState(false);
  const [updatingStatus, setUpdatingStatus] = useState(false);
  const [nextStatus, setNextStatus] = useState<SupplierStatus | "">("");
  const [error, setError] = useState<ActionError>(null);
  const [recheckStatus, setRecheckStatus] = useState<
    "idle" | "started" | "pending" | "completed" | "failed"
  >("idle");
  const pendingCheckId = useRef<string | null>(null);

  // #142: once a recheck is started, poll until the task settles (completed/failed) or
  // the window above runs out. Cleans up on unmount/re-trigger so a user navigating away
  // or clicking the button again never leaves a stray interval running.
  useEffect(() => {
    if (recheckStatus !== "pending") return;
    let attempts = 0;
    const checkId = pendingCheckId.current;
    const interval = setInterval(async () => {
      attempts += 1;
      try {
        const response = await fetch(`/api/suppliers/${supplier.id}/checks`);
        if (response.ok) {
          const checks = (await response.json()) as SupplierCheck[];
          const check = checks.find((c) => c.id === checkId);
          if (check && check.status !== "started") {
            clearInterval(interval);
            if (check.status === "failed") {
              setRecheckStatus("failed");
              setError({
                action: "recheck_failed",
                message: check.failureReason ?? t("suppliers.actions.checkFailedDefault"),
              });
            } else {
              setRecheckStatus("completed");
            }
            router.refresh();
            return;
          }
        }
      } catch {
        // Best-effort poll -- a transient failure here just waits for the next tick,
        // same "don't let a network blip look like a real error" discipline this app
        // uses elsewhere (e.g. proxy.ts's own token-refresh handling).
      }
      if (attempts >= RECHECK_POLL_MAX_ATTEMPTS) {
        clearInterval(interval);
        setRecheckStatus("idle"); // give up quietly; the check may still settle later
      }
    }, RECHECK_POLL_INTERVAL_MS);
    return () => clearInterval(interval);
    // `router`/`supplier.id` are stable for this component's lifetime; re-running on
    // every render would restart polling from attempt 0 each time.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [recheckStatus]);

  if (!canUpdate) return null;

  const allowedTargets = ALLOWED_STATUS_TRANSITIONS[supplier.status];

  async function handleRecheck() {
    setRechecking(true);
    setError(null);
    setRecheckStatus("idle");
    try {
      const response = await fetch(`/api/suppliers/${supplier.id}/recheck`, { method: "POST" });
      if (!response.ok) {
        const body = (await response.json().catch(() => null)) as { detail?: string } | null;
        setError({
          action: "recheck",
          message: body?.detail ?? t("suppliers.actions.startFailedDefault"),
        });
        return;
      }
      const check = (await response.json().catch(() => null)) as SupplierCheck | null;
      setRecheckStatus("started");
      router.refresh();
      if (check?.id) {
        pendingCheckId.current = check.id;
        setRecheckStatus("pending");
      }
    } catch {
      setError({ action: "recheck", message: t("errors.unreachableRetry") });
    } finally {
      setRechecking(false);
    }
  }

  async function handleStatusChange(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!nextStatus) return;
    setUpdatingStatus(true);
    setError(null);
    try {
      const response = await fetch(`/api/suppliers/${supplier.id}/status`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: nextStatus }),
      });
      if (!response.ok) {
        const body = (await response.json().catch(() => null)) as { detail?: string } | null;
        setError({
          action: "status",
          message: body?.detail ?? t("suppliers.actions.statusFailedDefault"),
        });
        return;
      }
      setNextStatus("");
      router.refresh();
    } catch {
      setError({ action: "status", message: t("errors.unreachableRetry") });
    } finally {
      setUpdatingStatus(false);
    }
  }

  return (
    <div className="flex flex-col items-end gap-3">
      <div className="flex flex-wrap items-center justify-end gap-2">
        {allowedTargets.length > 0 && (
          <form onSubmit={handleStatusChange} className="flex items-center gap-2">
            <label className="sr-only" htmlFor="supplier-next-status">
              {t("suppliers.actions.changeStatusLabel")}
            </label>
            <select
              id="supplier-next-status"
              value={nextStatus}
              onChange={(event) => setNextStatus(event.target.value as SupplierStatus)}
              disabled={updatingStatus}
              className={controlClasses}
            >
              <option value="">{t("suppliers.actions.changeStatus")}</option>
              {allowedTargets.map((candidate) => (
                <option key={candidate} value={candidate}>
                  {t(`status.supplier.${candidate}`)}
                </option>
              ))}
            </select>
            <Button
              type="submit"
              variant="secondary"
              loading={updatingStatus}
              disabled={!nextStatus}
            >
              {t("suppliers.actions.update")}
            </Button>
          </form>
        )}

        <Button variant="secondary" onClick={handleRecheck} loading={rechecking}>
          {t("suppliers.actions.runCheck")}
        </Button>
      </div>

      {(recheckStatus === "started" || recheckStatus === "pending") && !error && (
        <p className="text-xs font-medium text-success">
          {recheckStatus === "pending" ? t("suppliers.actions.startedInProgress") : t("suppliers.actions.started")}
        </p>
      )}

      {recheckStatus === "completed" && !error && (
        <p className="text-xs font-medium text-success">{t("suppliers.actions.completed")}</p>
      )}

      {error && (
        <Alert
          tone="danger"
          title={
            error.action === "status"
              ? t("suppliers.actions.statusRejected")
              : error.action === "recheck_failed"
                ? t("suppliers.actions.checkFailed")
                : t("suppliers.actions.couldNotStart")
          }
          className="w-full max-w-sm"
        >
          {error.message}
        </Alert>
      )}
    </div>
  );
}
