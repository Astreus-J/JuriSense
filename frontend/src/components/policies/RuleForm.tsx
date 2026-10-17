"use client";

import { useState } from "react";
import type { FormEvent } from "react";
import { useRouter } from "next/navigation";

import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Textarea } from "@/components/ui/Textarea";
import { useI18n } from "@/lib/i18n/client";
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
  const { t } = useI18n();
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
          title: t("policies.rule.invalidTitle"),
          body: body?.detail ?? t("policies.rule.invalidDefault"),
        });
      } else if (response.status === 409) {
        setError({
          title: t("policies.rule.conflictTitle"),
          body: body?.detail ?? t("policies.rule.conflictDefault"),
        });
      } else if (response.status === 403) {
        setError({
          title:
            mode === "create"
              ? t("policies.rule.forbiddenCreateTitle")
              : t("policies.rule.forbiddenEditTitle"),
          body:
            mode === "create"
              ? t("policies.rule.forbiddenCreateBody")
              : t("policies.rule.forbiddenEditBody"),
        });
      } else {
        setError({ title: t("errors.somethingWentWrong"), body: body?.detail ?? t("errors.tryAgain") });
      }
    } catch {
      setError({ title: t("errors.couldNotReachServer"), body: t("errors.tryAgain") });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4 rounded-lg border border-border-strong bg-surface-muted p-4">
      {error && (
        <Alert tone="danger" title={error.title}>
          {error.body}
        </Alert>
      )}

      <Textarea
        label={mode === "create" ? t("policies.rule.newYaml") : t("policies.rule.yaml")}
        name="yaml"
        required
        rows={12}
        value={yamlText}
        onChange={(event) => setYamlText(event.target.value)}
        disabled={submitting}
        placeholder={RULE_YAML_PLACEHOLDER}
        hint={t("policies.rule.yamlHint")}
        className="font-mono text-xs!"
      />

      <div className="flex items-center gap-2">
        <Button type="submit" loading={submitting}>
          {mode === "create" ? t("policies.rule.create") : t("policies.rule.save")}
        </Button>
        <Button type="button" variant="ghost" onClick={onCancel} disabled={submitting}>
          {t("common.cancel")}
        </Button>
      </div>
    </form>
  );
}
