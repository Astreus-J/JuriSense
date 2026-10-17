"use client";

import { useState } from "react";
import type { FormEvent } from "react";
import { useRouter } from "next/navigation";
import { Eye, EyeOff, Lock, Mail } from "lucide-react";

import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { useI18n } from "@/lib/i18n/client";
import type { Translator } from "@/lib/i18n/translate";

interface LoginFormProps {
  /** Where to send the user after a successful login. */
  next: string;
}

type LoginErrorState =
  | { kind: "invalid_credentials" }
  | { kind: "locked"; retryAfterSeconds?: number }
  | { kind: "unexpected" }
  | null;

function errorMessage(error: LoginErrorState, { t }: Translator): { title: string; body?: string } | null {
  if (!error) return null;
  switch (error.kind) {
    case "invalid_credentials":
      return { title: t("auth.signIn.invalidCredentials") };
    case "locked": {
      // #134: `retryAfterSeconds` of `0` ("you can try again right now") is falsy, so the
      // original `? :` skipped straight to the generic fallback message -- actively
      // misleading in that exact case (told the user to wait when they didn't have to).
      // Checking for `undefined` explicitly, and special-casing `<= 0`, fixes both ends.
      let body = t("auth.signIn.lockedGeneric");
      if (error.retryAfterSeconds !== undefined) {
        body =
          error.retryAfterSeconds > 0
            ? t("auth.signIn.lockedMinutes", { count: Math.ceil(error.retryAfterSeconds / 60) })
            : t("auth.signIn.lockedNow");
      }
      return { title: t("auth.signIn.lockedTitle"), body };
    }
    case "unexpected":
      return { title: t("errors.somethingWentWrong"), body: t("errors.tryAgainShortly") };
  }
}

export function LoginForm({ next }: LoginFormProps) {
  const router = useRouter();
  const i18n = useI18n();
  const { t } = i18n;
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
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

  const message = errorMessage(error, i18n);

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-5">
      {message && (
        <Alert tone="danger" title={message.title}>
          {message.body}
        </Alert>
      )}

      <Field
        label={t("auth.signIn.email")}
        type="email"
        name="email"
        leading={<Mail aria-hidden="true" />}
        autoComplete="email"
        required
        value={email}
        onChange={(event) => setEmail(event.target.value)}
        disabled={submitting}
      />

      <Field
        label={t("auth.signIn.password")}
        type={showPassword ? "text" : "password"}
        name="password"
        leading={<Lock aria-hidden="true" />}
        trailing={
          <button
            type="button"
            onClick={() => setShowPassword((visible) => !visible)}
            aria-label={t("auth.signIn.showPassword")}
            aria-pressed={showPassword}
            disabled={submitting}
            className="flex size-8 items-center justify-center rounded-md text-foreground-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring disabled:opacity-60"
          >
            {showPassword ? <EyeOff className="size-4" aria-hidden="true" /> : <Eye className="size-4" aria-hidden="true" />}
          </button>
        }
        autoComplete="current-password"
        required
        value={password}
        onChange={(event) => setPassword(event.target.value)}
        disabled={submitting}
      />

      <div className="flex justify-center">
        <Button type="submit" loading={submitting} className="px-8!">
          {submitting ? t("auth.signIn.submitting") : t("auth.signIn.submit")}
        </Button>
      </div>
    </form>
  );
}
