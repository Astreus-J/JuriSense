"use client";

import { useState } from "react";
import type { FormEvent } from "react";
import { useRouter } from "next/navigation";

import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";

type FormErrorState = { title: string; body?: string } | null;

/**
 * Creating a Policy always creates its first draft `PolicyVersion` in the same backend
 * call (`policy_service.create_policy`) — there is nothing else to configure up front, so
 * this form only asks for a name and sends the reviewer straight to the policy detail
 * page to start adding rules, matching `CreateSupplierForm`'s exact shape/error-handling
 * pattern.
 */
export function CreatePolicyForm() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<FormErrorState>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      const response = await fetch("/api/policies", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      });

      if (response.ok) {
        const created = (await response.json()) as { policy: { id: string } };
        router.push(`/policies/${created.policy.id}`);
        router.refresh();
        return;
      }

      const body = (await response.json().catch(() => null)) as { detail?: string } | null;
      if (response.status === 403) {
        setError({
          title: "You can't create policies",
          body: 'Ask an administrator to grant you the "policies" create permission.',
        });
      } else if (response.status === 400) {
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
    <form onSubmit={handleSubmit} noValidate className="space-y-5">
      {error && (
        <Alert tone="danger" title={error.title}>
          {error.body}
        </Alert>
      )}

      <Field
        label="Policy name"
        name="name"
        autoComplete="off"
        required
        hint="A short, recognizable name, e.g. “Vendor Compliance” or “Data Privacy”. You'll add rules once it's created."
        value={name}
        onChange={(event) => setName(event.target.value)}
        disabled={submitting}
      />

      <Button type="submit" loading={submitting}>
        {submitting ? "Creating…" : "Create policy"}
      </Button>
    </form>
  );
}
