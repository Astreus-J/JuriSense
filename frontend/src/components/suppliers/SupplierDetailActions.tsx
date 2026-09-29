"use client";

import { useState } from "react";
import type { FormEvent } from "react";
import { useRouter } from "next/navigation";

import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { ALLOWED_STATUS_TRANSITIONS, SUPPLIER_STATUS_LABELS } from "@/lib/suppliers/types";
import type { Supplier, SupplierStatus } from "@/lib/suppliers/types";

interface SupplierDetailActionsProps {
  supplier: Supplier;
  canUpdate: boolean;
}

type ActionError = { action: "recheck" | "status"; message: string } | null;

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
  const [rechecking, setRechecking] = useState(false);
  const [updatingStatus, setUpdatingStatus] = useState(false);
  const [nextStatus, setNextStatus] = useState<SupplierStatus | "">("");
  const [error, setError] = useState<ActionError>(null);
  const [recheckStarted, setRecheckStarted] = useState(false);

  if (!canUpdate) return null;

  const allowedTargets = ALLOWED_STATUS_TRANSITIONS[supplier.status];

  async function handleRecheck() {
    setRechecking(true);
    setError(null);
    setRecheckStarted(false);
    try {
      const response = await fetch(`/api/suppliers/${supplier.id}/recheck`, { method: "POST" });
      if (!response.ok) {
        const body = (await response.json().catch(() => null)) as { detail?: string } | null;
        setError({
          action: "recheck",
          message: body?.detail ?? "Could not start a new verification check.",
        });
        return;
      }
      setRecheckStarted(true);
      router.refresh();
    } catch {
      setError({ action: "recheck", message: "Could not reach the server. Try again." });
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
          message: body?.detail ?? "Could not update the supplier's status.",
        });
        return;
      }
      setNextStatus("");
      router.refresh();
    } catch {
      setError({ action: "status", message: "Could not reach the server. Try again." });
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
              Change supplier status
            </label>
            <select
              id="supplier-next-status"
              value={nextStatus}
              onChange={(event) => setNextStatus(event.target.value as SupplierStatus)}
              disabled={updatingStatus}
              className="rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-focus-ring"
            >
              <option value="">Change status…</option>
              {allowedTargets.map((candidate) => (
                <option key={candidate} value={candidate}>
                  {SUPPLIER_STATUS_LABELS[candidate]}
                </option>
              ))}
            </select>
            <Button
              type="submit"
              variant="secondary"
              loading={updatingStatus}
              disabled={!nextStatus}
            >
              Update
            </Button>
          </form>
        )}

        <Button variant="secondary" onClick={handleRecheck} loading={rechecking}>
          Run verification check
        </Button>
      </div>

      {recheckStarted && !error && (
        <p className="text-xs font-medium text-success">New verification check started.</p>
      )}

      {error && (
        <Alert
          tone="danger"
          title={error.action === "status" ? "Status change rejected" : "Could not start check"}
          className="w-full max-w-sm"
        >
          {error.message}
        </Alert>
      )}
    </div>
  );
}
