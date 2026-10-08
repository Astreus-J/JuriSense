"use client";

import { useState } from "react";
import type { FormEvent } from "react";
import { useRouter } from "next/navigation";

import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Textarea } from "@/components/ui/Textarea";
import { RULE_YAML_PLACEHOLDER } from "@/lib/policies/ruleYaml";

type FormErrorState = { title: string; body?: string } | null;

interface RuleFormProps {
  policyId: string;
  versionId: string;
  mode: "create" | "edit";
  /** Required when `mode === "edit"`. */
  ruleId?: string;
  initialYaml?: string;
  onCancel: () => void;
  onSuccess: () => void;
}

/**
 * Shared create/edit form for one Rule's YAML (ADR-004: "Policy authors interact with
 * YAML... not raw CEL/JSONLogic") — the one meaningful difference between the two modes
 * is which endpoint/method it posts to, so a single component avoids duplicating the
 * YAML textarea, loading state, and error handling across two files.
 *
 * 422 (malformed YAML/grammar) is surfaced verbatim — `RuleValidationError.message` is
 * written to be read by whoever authors the policy (`backend/app/policies/domain/
 * errors.py`), not an internal detail to hide.
 */
export function RuleForm({ policyId, versionId, mode, ruleId, initialYaml, onCancel, onSuccess }: RuleFormProps) {
  const router = useRouter();
  const [yamlText, setYamlText] = useState(initialYaml ?? "");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<FormErrorState>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);

    const url =
      mode === "create"
        ? `/api/policies/${policyId}/versions/${versionId}/rules`
        : `/api/policies/${policyId}/versions/${versionId}/rules/${ruleId}`;

    try {
      const response = await fetch(url, {
        method: mode === "create" ? "POST" : "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ yaml: yamlText }),
      });

      if (response.ok) {
        router.refresh();
        onSuccess();
        return;
      }

      const body = (await response.json().catch(() => null)) as { detail?: string } | null;
      if (response.status === 422) {
        setError({
          title: "This rule's YAML is invalid",
          body: body?.detail ?? "Check the YAML against the supported grammar and try again.",
        });
      } else if (response.status === 409) {
        setError({
          title: "Could not save this rule",
          body:
            body?.detail ??
            "This policy version can no longer accept rule changes, or its rule id is already used.",
        });
      } else if (response.status === 403) {
        setError({
          title: mode === "create" ? "You can't add rules" : "You can't edit rules",
          body: `Ask an administrator to grant you the "policies" ${mode === "create" ? "create" : "update"} permission.`,
        });
      } else {
        setError({ title: "Something went wrong.", body: body?.detail ?? "Please try again." });
      }
    } catch {
      setError({ title: "Could not reach the server.", body: "Please try again." });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4 rounded-xl border border-border bg-surface p-4">
      {error && (
        <Alert tone="danger" title={error.title}>
          {error.body}
        </Alert>
      )}

      <Textarea
        label={mode === "create" ? "New rule (YAML)" : "Rule YAML"}
        name="yaml"
        required
        rows={12}
        value={yamlText}
        onChange={(event) => setYamlText(event.target.value)}
        disabled={submitting}
        placeholder={RULE_YAML_PLACEHOLDER}
        hint="Author the rule exactly as policy YAML — see docs/03-domain/policy-engine.md for the full rule, severity, and operator grammar."
        className="font-mono text-xs"
      />

      <div className="flex items-center gap-2">
        <Button type="submit" loading={submitting}>
          {mode === "create" ? "Add rule" : "Save changes"}
        </Button>
        <Button type="button" variant="ghost" onClick={onCancel} disabled={submitting}>
          Cancel
        </Button>
      </div>
    </form>
  );
}
