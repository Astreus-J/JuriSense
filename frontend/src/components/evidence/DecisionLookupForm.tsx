"use client";

import { useState } from "react";
import type { FormEvent } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/**
 * STORY-7.3.1's one navigation entry point into the Decision Passport: there is no
 * "browse all decisions" list in this story's scope (see `/decisions/[id]/page.tsx`'s own
 * docstring), so this is a plain id lookup — pure client-side navigation, no fetch of its
 * own, since `/decisions/[id]` does the real request and already handles every error case
 * (404/403) as a full page.
 */
export function DecisionLookupForm() {
  const router = useRouter();
  const [decisionId, setDecisionId] = useState("");
  const [error, setError] = useState<string | null>(null);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = decisionId.trim();
    if (!UUID_PATTERN.test(trimmed)) {
      setError("Enter a valid decision id.");
      return;
    }
    setError(null);
    router.push(`/decisions/${trimmed}`);
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3 sm:flex-row sm:items-end">
      <div className="flex-1">
        <Field
          label="Decision id"
          placeholder="e.g. 3fa85f64-5717-4562-b3fc-2c963f66afa6"
          value={decisionId}
          onChange={(event) => setDecisionId(event.target.value)}
          error={error ?? undefined}
        />
      </div>
      <Button type="submit">View Decision Passport</Button>
    </form>
  );
}
