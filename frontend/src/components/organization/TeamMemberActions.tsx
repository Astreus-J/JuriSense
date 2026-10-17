"use client";

import { useState } from "react";
import type { FormEvent } from "react";
import { useRouter } from "next/navigation";

import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { compactControlClasses } from "@/components/ui/Field";
import { ROLES } from "@/lib/auth/types";
import { useI18n } from "@/lib/i18n/client";
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
  const { t } = useI18n();
  const [nextRole, setNextRole] = useState<Role | "">("");
  const [updatingRole, setUpdatingRole] = useState(false);
  const [confirmingDeactivate, setConfirmingDeactivate] = useState(false);
  const [deactivating, setDeactivating] = useState(false);
  const [error, setError] = useState<ActionError>(null);

  if (isSelf) {
    return <span className="text-xs text-foreground-muted">{t("organization.team.you")}</span>;
  }

  if (!member.isActive) {
    return <span className="text-xs text-foreground-muted">{t("organization.team.deactivated")}</span>;
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
        setError({ action: "role", message: body?.detail ?? t("organization.team.roleFailedDefault") });
        return;
      }
      setNextRole("");
      router.refresh();
    } catch {
      setError({ action: "role", message: t("errors.unreachableRetry") });
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
          message: body?.detail ?? t("organization.team.deactivateFailedDefault"),
        });
        return;
      }
      setConfirmingDeactivate(false);
      router.refresh();
    } catch {
      setError({ action: "deactivate", message: t("errors.unreachableRetry") });
    } finally {
      setDeactivating(false);
    }
  }

  return (
    <div className="flex flex-col items-end gap-2">
      <div className="flex flex-wrap items-center justify-end gap-2">
        <form onSubmit={handleRoleChange} className="flex items-center gap-2">
          <label className="sr-only" htmlFor={`role-${member.id}`}>
            {t("organization.team.changeRoleLabel", { name: member.fullName })}
          </label>
          <select
            id={`role-${member.id}`}
            value={nextRole}
            onChange={(event) => setNextRole(event.target.value as Role)}
            disabled={updatingRole}
            className={compactControlClasses}
          >
            <option value="">{t("organization.team.changeRole")}</option>
            {ROLES.filter((role) => role !== member.role).map((role) => (
              <option key={role} value={role}>
                {t(`role.${role}`)}
              </option>
            ))}
          </select>
          <Button type="submit" size="sm" variant="secondary" loading={updatingRole} disabled={!nextRole}>
            {t("organization.team.update")}
          </Button>
        </form>

        {confirmingDeactivate ? (
          <div className="flex items-center gap-2">
            <span className="text-xs text-foreground-muted">{t("organization.team.deactivateQuestion")}</span>
            <Button size="sm" variant="danger" onClick={handleDeactivate} loading={deactivating}>
              {t("organization.team.confirm")}
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setConfirmingDeactivate(false)}
              disabled={deactivating}
            >
              {t("common.cancel")}
            </Button>
          </div>
        ) : (
          <Button size="sm" variant="secondary" onClick={() => setConfirmingDeactivate(true)}>
            {t("organization.team.deactivate")}
          </Button>
        )}
      </div>

      {error && (
        <Alert
          tone="danger"
          title={
            error.action === "role"
              ? t("organization.team.roleChangeRejected")
              : t("organization.team.couldNotDeactivate")
          }
          className="w-full max-w-xs"
        >
          {error.message}
        </Alert>
      )}
    </div>
  );
}
