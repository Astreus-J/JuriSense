"use client";

import { useState } from "react";
import type { FormEvent } from "react";
import { useRouter } from "next/navigation";

import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { controlClasses } from "@/components/ui/Field";
import { Field } from "@/components/ui/Field";
import { ROLES } from "@/lib/auth/types";
import { useI18n } from "@/lib/i18n/client";
import type { Role } from "@/lib/auth/types";

type FormErrorState = { title: string; body?: string } | null;

/**
 * Admin-only — `OrganizationSettingsPage` only renders this when
 * `getOrganizationPermissions(role).canManageTeam` is true, matching `CreateSupplierForm`'s
 * reachability stance: the real guard is `POST /api/users/invites`'s server-side
 * `CurrentAdmin` dependency, not this hint. Resending to an email with a pending invitation
 * silently replaces it (`invite_service.invite_user`'s own docstring), so there's no special
 * "already invited" error path to design for here.
 */
export function InviteUserForm() {
  const router = useRouter();
  const { t } = useI18n();
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState<Role>("viewer");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<FormErrorState>(null);
  const [sentTo, setSentTo] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    setSentTo(null);

    try {
      const response = await fetch("/api/users/invites", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, role, fullName: fullName || undefined }),
      });

      if (response.ok) {
        setSentTo(email);
        setEmail("");
        setFullName("");
        setRole("viewer");
        router.refresh();
        return;
      }

      const body = (await response.json().catch(() => null)) as { detail?: string } | null;
      if (response.status === 409) {
        setError({
          title: t("organization.invite.alreadyTitle"),
          body: body?.detail ?? t("organization.invite.alreadyBody"),
        });
      } else if (response.status === 402) {
        setError({
          title: t("organization.invite.seatTitle"),
          body: body?.detail ?? t("organization.invite.seatBody"),
        });
      } else if (response.status === 403) {
        setError({
          title: t("organization.invite.forbiddenTitle"),
          body: t("organization.invite.forbiddenBody"),
        });
      } else if (response.status === 422) {
        setError({
          title: t("organization.invite.checkTitle"),
          body: body?.detail ?? t("organization.invite.checkBody"),
        });
      } else {
        setError({ title: t("errors.somethingWentWrong"), body: t("errors.tryAgainShortly") });
      }
    } catch {
      setError({ title: t("errors.couldNotReachServer"), body: t("errors.tryAgain") });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-4">
      {error && (
        <Alert tone="danger" title={error.title}>
          {error.body}
        </Alert>
      )}
      {sentTo && !error && (
        <Alert tone="success" title={t("organization.invite.sentTitle")}>
          {t("organization.invite.sentBody", { email: sentTo })}
        </Alert>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        <Field
          label={t("organization.invite.email")}
          name="email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          disabled={submitting}
        />
        <Field
          label={t("organization.invite.fullName")}
          name="fullName"
          autoComplete="name"
          hint={t("organization.invite.fullNameHint")}
          value={fullName}
          onChange={(event) => setFullName(event.target.value)}
          disabled={submitting}
        />
      </div>

      <div className="space-y-1.5">
        <label htmlFor="invite-role" className="block text-sm font-medium text-foreground">
          {t("organization.invite.role")}
        </label>
        <select
          id="invite-role"
          value={role}
          onChange={(event) => setRole(event.target.value as Role)}
          disabled={submitting}
          className={`w-full sm:w-64 ${controlClasses}`}
        >
          {ROLES.map((candidate) => (
            <option key={candidate} value={candidate}>
              {t(`role.${candidate}`)}
            </option>
          ))}
        </select>
      </div>

      <Button type="submit" loading={submitting}>
        {submitting ? t("organization.invite.submitting") : t("organization.invite.submit")}
      </Button>
    </form>
  );
}
