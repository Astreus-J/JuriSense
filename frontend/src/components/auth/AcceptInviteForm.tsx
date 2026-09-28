"use client";

import { useState } from "react";
import type { FormEvent } from "react";
import { useRouter } from "next/navigation";

import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";

interface AcceptInviteFormProps {
  token: string;
}

type SubmitErrorState = { title: string; body?: string } | null;

export function AcceptInviteForm({ token }: AcceptInviteFormProps) {
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<SubmitErrorState>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    if (password !== confirmPassword) {
      setError({ title: "Passwords don't match.", body: "Re-enter both fields to confirm." });
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
        router.push("/dashboard");
        router.refresh();
        return;
      }

      const body = (await response.json().catch(() => null)) as { detail?: string } | null;
      if (response.status === 400) {
        setError({
          title: "This invitation link is invalid or has expired.",
          body: "Ask your admin to send you a new invitation.",
        });
      } else if (response.status === 422) {
        setError({ title: "Choose a stronger password.", body: body?.detail });
      } else {
        setError({ title: "Something went wrong.", body: "Please try again in a moment." });
      }
    } catch {
      setError({ title: "Something went wrong.", body: "Please try again in a moment." });
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
        label="Full name"
        type="text"
        name="fullName"
        autoComplete="name"
        value={fullName}
        onChange={(event) => setFullName(event.target.value)}
        disabled={submitting}
        hint="Optional if your admin already set it when inviting you."
      />

      <Field
        label="Choose a password"
        type="password"
        name="password"
        autoComplete="new-password"
        required
        value={password}
        onChange={(event) => setPassword(event.target.value)}
        disabled={submitting}
      />

      <Field
        label="Confirm password"
        type="password"
        name="confirmPassword"
        autoComplete="new-password"
        required
        value={confirmPassword}
        onChange={(event) => setConfirmPassword(event.target.value)}
        disabled={submitting}
      />

      <Button type="submit" loading={submitting} className="w-full">
        {submitting ? "Setting up your account…" : "Accept invitation"}
      </Button>
    </form>
  );
}
