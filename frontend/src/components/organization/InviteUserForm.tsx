"use client";

import { useState } from "react";
import type { FormEvent } from "react";
import { useRouter } from "next/navigation";

import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { formatRoleLabel, ROLES } from "@/lib/auth/types";
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
          title: "Already registered",
          body: body?.detail ?? "A user with this email already exists.",
        });
      } else if (response.status === 402) {
        setError({
          title: "Seat limit reached",
          body: body?.detail ?? "Your plan's user limit has been reached.",
        });
      } else if (response.status === 403) {
        setError({
          title: "You can't invite teammates",
          body: "Ask an organization admin to send the invitation.",
        });
      } else if (response.status === 422) {
        setError({ title: "Check the form", body: body?.detail ?? "Some fields are invalid." });
      } else {
        setError({ title: "Something went wrong.", body: "Please try again in a moment." });
      }
    } catch {
      setError({ title: "Could not reach the server.", body: "Please try again." });
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
        <Alert tone="success" title="Invitation sent">
          {sentTo} will receive an email with a link to set up their account.
        </Alert>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        <Field
          label="Email"
          name="email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          disabled={submitting}
        />
        <Field
          label="Full name"
          name="fullName"
          autoComplete="name"
          hint="Optional — the invitee can set it when they accept."
          value={fullName}
          onChange={(event) => setFullName(event.target.value)}
          disabled={submitting}
        />
      </div>

      <div className="space-y-1.5">
        <label htmlFor="invite-role" className="block text-sm font-medium text-foreground">
          Role
        </label>
        <select
          id="invite-role"
          value={role}
          onChange={(event) => setRole(event.target.value as Role)}
          disabled={submitting}
          className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-focus-ring sm:w-64"
        >
          {ROLES.map((candidate) => (
            <option key={candidate} value={candidate}>
              {formatRoleLabel(candidate)}
            </option>
          ))}
        </select>
      </div>

      <Button type="submit" loading={submitting}>
        {submitting ? "Sending invite…" : "Send invitation"}
      </Button>
    </form>
  );
}
