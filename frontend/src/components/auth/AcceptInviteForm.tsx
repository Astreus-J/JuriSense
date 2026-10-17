"use client";

import { useState } from "react";
import type { FormEvent } from "react";
import { useRouter } from "next/navigation";

import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { useI18n } from "@/lib/i18n/client";

interface AcceptInviteFormProps {
  token: string;
}

type SubmitErrorState = { title: string; body?: string } | null;

export function AcceptInviteForm({ token }: AcceptInviteFormProps) {
  const router = useRouter();
  const { t } = useI18n();
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<SubmitErrorState>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    if (password !== confirmPassword) {
      setError({ title: t("auth.invite.mismatchTitle"), body: t("auth.invite.mismatchBody") });
      return;
    }

    setSubmitting(true);
    try {
      const response = await fetch("/api/session/accept-invite", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, password, fullName: fullName || undefined }),
      });

      if (response.ok) {
        const result = (await response.json().catch(() => null)) as {
          requiresManualLogin?: boolean;
        } | null;
        // #131: the account was created either way -- if the follow-up login failed
        // server-side, send them to a normal sign-in instead of the dashboard rather
        // than treating this as a dead end.
        if (result?.requiresManualLogin) {
          router.push("/login?accountCreated=1");
          return;
        }
        router.push("/dashboard");
        router.refresh();
        return;
      }

      const body = (await response.json().catch(() => null)) as { detail?: string } | null;
      if (response.status === 400) {
        setError({
          title: t("auth.invite.invalidTitle"),
          body: t("auth.invite.invalidBody"),
        });
      } else if (response.status === 422) {
        setError({ title: t("auth.invite.weakPasswordTitle"), body: body?.detail });
      } else {
        setError({ title: t("errors.somethingWentWrong"), body: t("errors.tryAgainShortly") });
      }
    } catch {
      setError({ title: t("errors.somethingWentWrong"), body: t("errors.tryAgainShortly") });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-5">
      {error && (
        <Alert tone="danger" title={error.title}>
          {error.body}
        </Alert>
      )}

      <Field
        label={t("auth.invite.fullName")}
        type="text"
        name="fullName"
        autoComplete="name"
        value={fullName}
        onChange={(event) => setFullName(event.target.value)}
        disabled={submitting}
        hint={t("auth.invite.fullNameHint")}
      />

      <Field
        label={t("auth.invite.password")}
        type="password"
        name="password"
        autoComplete="new-password"
        required
        value={password}
        onChange={(event) => setPassword(event.target.value)}
        disabled={submitting}
      />

      <Field
        label={t("auth.invite.confirmPassword")}
        type="password"
        name="confirmPassword"
        autoComplete="new-password"
        required
        value={confirmPassword}
        onChange={(event) => setConfirmPassword(event.target.value)}
        disabled={submitting}
      />

      <Button type="submit" loading={submitting} className="w-full">
        {submitting ? t("auth.invite.submitting") : t("auth.invite.submit")}
      </Button>
    </form>
  );
}
