"use client";

import { useState } from "react";
import type { FormEvent } from "react";
import { useRouter } from "next/navigation";

import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";

interface LoginFormProps {
  /** Where to send the user after a successful login. */
  next: string;
}

type LoginErrorState =
  | { kind: "invalid_credentials" }
  | { kind: "locked"; retryAfterSeconds?: number }
  | { kind: "unexpected" }
  | null;

function errorMessage(error: LoginErrorState): { title: string; body?: string } | null {
  if (!error) return null;
  switch (error.kind) {
    case "invalid_credentials":
      return { title: "Invalid email or password." };
    case "locked":
      return {
        title: "Too many failed attempts.",
        body: error.retryAfterSeconds
          ? `Try again in about ${Math.ceil(error.retryAfterSeconds / 60)} minute(s).`
          : "Try again in a few minutes.",
      };
    case "unexpected":
      return { title: "Something went wrong.", body: "Please try again in a moment." };
  }
}

export function LoginForm({ next }: LoginFormProps) {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<LoginErrorState>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      const response = await fetch("/api/session/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      if (response.ok) {
        router.push(next);
        router.refresh();
        return;
      }

      if (response.status === 401) {
        setError({ kind: "invalid_credentials" });
      } else if (response.status === 429) {
        const body = (await response.json().catch(() => null)) as {
          retryAfterSeconds?: number;
        } | null;
        setError({ kind: "locked", retryAfterSeconds: body?.retryAfterSeconds });
      } else {
        setError({ kind: "unexpected" });
      }
    } catch {
      setError({ kind: "unexpected" });
    } finally {
      setSubmitting(false);
    }
  }

  const message = errorMessage(error);

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-5">
      {message && (
        <Alert tone="danger" title={message.title}>
          {message.body}
        </Alert>
      )}

      <Field
        label="Work email"
        type="email"
        name="email"
        autoComplete="email"
        required
        value={email}
        onChange={(event) => setEmail(event.target.value)}
        disabled={submitting}
      />

      <Field
        label="Password"
        type="password"
        name="password"
        autoComplete="current-password"
        required
        value={password}
        onChange={(event) => setPassword(event.target.value)}
        disabled={submitting}
      />

      <Button type="submit" loading={submitting} className="w-full">
        {submitting ? "Signing in…" : "Sign in"}
      </Button>
    </form>
  );
}
