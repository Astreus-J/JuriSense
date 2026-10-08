"use client";

import { useState } from "react";
import type { FormEvent } from "react";
import { useRouter } from "next/navigation";

import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { formatRoleLabel, ROLES } from "@/lib/auth/types";
import type { Role } from "@/lib/auth/types";
import type { TeamMember } from "@/lib/organization/types";

interface TeamMemberActionsProps {
  member: TeamMember;
  /** The row for the admin currently viewing the screen — the backend rejects an admin
   * changing their own role/status or deactivating their own account
   * (`OperationNotAllowedError` in `user_service.py`), so this mirrors that rule instead of
   * letting every admin discover it as a 400. */
  isSelf: boolean;
}

type ActionError = { action: "role" | "deactivate"; message: string } | null;

/**
 * Role-change and deactivate controls for one team-member row. `TeamTable` only renders this
 * when the viewer passed `getOrganizationPermissions(role).canManageTeam` (admin), but the
 * real guard is server-side on every submit (`CurrentAdmin`), same stance as
 * `SupplierDetailActions`: a 403/400 here is a normal, handled error state, not a crash.
 */
export function TeamMemberActions({ member, isSelf }: TeamMemberActionsProps) {
  const router = useRouter();
  const [nextRole, setNextRole] = useState<Role | "">("");
  const [updatingRole, setUpdatingRole] = useState(false);
  const [confirmingDeactivate, setConfirmingDeactivate] = useState(false);
  const [deactivating, setDeactivating] = useState(false);
  const [error, setError] = useState<ActionError>(null);

  if (isSelf) {
    return <span className="text-xs text-foreground-muted">That&apos;s you</span>;
  }

  if (!member.isActive) {
    return <span className="text-xs text-foreground-muted">Deactivated</span>;
  }

  async function handleRoleChange(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!nextRole || nextRole === member.role) return;
    setUpdatingRole(true);
    setError(null);
    try {
      const response = await fetch(`/api/users/${member.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ role: nextRole }),
      });
      if (!response.ok) {
        const body = (await response.json().catch(() => null)) as { detail?: string } | null;
        setError({ action: "role", message: body?.detail ?? "Could not update the role." });
        return;
      }
      setNextRole("");
      router.refresh();
    } catch {
      setError({ action: "role", message: "Could not reach the server. Try again." });
    } finally {
      setUpdatingRole(false);
    }
  }

  async function handleDeactivate() {
    setDeactivating(true);
    setError(null);
    try {
      const response = await fetch(`/api/users/${member.id}`, { method: "DELETE" });
      if (!response.ok) {
        const body = (await response.json().catch(() => null)) as { detail?: string } | null;
        setError({
          action: "deactivate",
          message: body?.detail ?? "Could not deactivate this user.",
        });
        return;
      }
      setConfirmingDeactivate(false);
      router.refresh();
    } catch {
      setError({ action: "deactivate", message: "Could not reach the server. Try again." });
    } finally {
      setDeactivating(false);
    }
  }

  return (
    <div className="flex flex-col items-end gap-2">
      <div className="flex flex-wrap items-center justify-end gap-2">
        <form onSubmit={handleRoleChange} className="flex items-center gap-2">
          <label className="sr-only" htmlFor={`role-${member.id}`}>
            Change role for {member.fullName}
          </label>
          <select
            id={`role-${member.id}`}
            value={nextRole}
            onChange={(event) => setNextRole(event.target.value as Role)}
            disabled={updatingRole}
            className="rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-focus-ring"
          >
            <option value="">Change role…</option>
            {ROLES.filter((role) => role !== member.role).map((role) => (
              <option key={role} value={role}>
                {formatRoleLabel(role)}
              </option>
            ))}
          </select>
          <Button type="submit" variant="secondary" loading={updatingRole} disabled={!nextRole}>
            Update
          </Button>
        </form>

        {confirmingDeactivate ? (
          <div className="flex items-center gap-2">
            <span className="text-xs text-foreground-muted">Deactivate?</span>
            <Button variant="danger" onClick={handleDeactivate} loading={deactivating}>
              Confirm
            </Button>
            <Button
              variant="ghost"
              onClick={() => setConfirmingDeactivate(false)}
              disabled={deactivating}
            >
              Cancel
            </Button>
          </div>
        ) : (
          <Button variant="secondary" onClick={() => setConfirmingDeactivate(true)}>
            Deactivate
          </Button>
        )}
      </div>

      {error && (
        <Alert
          tone="danger"
          title={error.action === "role" ? "Role change rejected" : "Could not deactivate"}
          className="w-full max-w-xs"
        >
          {error.message}
        </Alert>
      )}
    </div>
  );
}
