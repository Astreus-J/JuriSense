"use client";

import { useMemo, useState } from "react";
import type { FormEvent } from "react";
import { useRouter } from "next/navigation";
import { CheckCircle2, ShieldAlert } from "lucide-react";

import { Alert } from "@/components/ui/Alert";
import { Badge } from "@/components/ui/Badge";
import { controlClasses } from "@/components/ui/Field";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/cn";
import { useI18n } from "@/lib/i18n/client";
import type { Translator } from "@/lib/i18n/translate";
import { expectedTypeForPath, formatFieldPath, getLeafAtPath } from "@/lib/contracts/extractedData";
import { formatConfidence } from "@/lib/format";
import type { LeafType } from "@/lib/contracts/extractedData";
import type { ContractFields, ExtractedLeaf } from "@/lib/contracts/types";

const INPUT_CLASSES = `w-full ${controlClasses}`;

interface ConfirmationFormProps {
  contractId: string;
  versionId: string;
  fields: ContractFields;
  needsConfirmationPaths: string[];
  /** UI-only hint from `getContractPermissions` — the submit still goes through the real
   * `PATCH .../confirm` permission check; see that function's own docstring. */
  canUpdate: boolean;
}

type FieldMode = "accept" | "correct";
type FieldState = { mode: FieldMode; raw: string };
type FormErrorState = { title: string; body?: string } | null;

function describeValue(value: unknown, { t }: Translator): string {
  if (typeof value === "boolean") return value ? t("contracts.confirm.yes") : t("contracts.confirm.no");
  if (typeof value === "object" && value !== null) return JSON.stringify(value);
  return String(value ?? "—");
}

// QA review (2026-09-30): dispatch on the field's documented schema type
// (`expectedTypeForPath`), never `typeof value` — `value` is frequently `null` for
// exactly the low-confidence fields this form handles, and `typeof null === "object"`
// tells you nothing about whether the field is *meant* to be a boolean, a number, or an
// object. See `expectedTypeForPath`'s own docstring for the full failure mode this
// replaces.
function initialRawValue(value: unknown, type: LeafType): string {
  if (type === "boolean") return value === true ? "true" : value === false ? "false" : "true";
  if (type === "object") return JSON.stringify(value ?? (Array.isArray(value) ? [] : {}), null, 2);
  return value === null || value === undefined ? "" : String(value);
}

function parseCorrectionValue(
  type: LeafType,
  raw: string,
  { t }: Translator,
): { ok: true; value: unknown } | { ok: false; error: string } {
  if (type === "boolean") {
    if (raw !== "true" && raw !== "false") return { ok: false, error: t("contracts.confirm.chooseYesNo") };
    return { ok: true, value: raw === "true" };
  }
  if (type === "number") {
    // Number("") === 0 in JS -- an empty/blank input must not silently become 0.
    if (raw.trim().length === 0) return { ok: false, error: t("contracts.confirm.validNumber") };
    const parsed = Number(raw);
    if (Number.isNaN(parsed)) return { ok: false, error: t("contracts.confirm.validNumber") };
    return { ok: true, value: parsed };
  }
  if (type === "object") {
    try {
      return { ok: true, value: JSON.parse(raw) };
    } catch {
      return { ok: false, error: t("contracts.confirm.validJson") };
    }
  }
  if (raw.trim().length === 0) {
    return { ok: false, error: t("contracts.confirm.notEmpty") };
  }
  return { ok: true, value: raw };
}

function CorrectionInput({
  type,
  value,
  onChange,
  disabled,
}: {
  type: LeafType;
  value: string;
  onChange: (value: string) => void;
  disabled: boolean;
}) {
  const { t } = useI18n();
  if (type === "boolean") {
    return (
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        disabled={disabled}
        className={INPUT_CLASSES}
      >
        <option value="true">{t("contracts.confirm.yes")}</option>
        <option value="false">{t("contracts.confirm.no")}</option>
      </select>
    );
  }
  if (type === "number") {
    return (
      <input
        type="number"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        disabled={disabled}
        className={INPUT_CLASSES}
      />
    );
  }
  if (type === "object") {
    return (
      <textarea
        value={value}
        onChange={(event) => onChange(event.target.value)}
        disabled={disabled}
        rows={4}
        className={cn(INPUT_CLASSES, "font-mono text-xs")}
      />
    );
  }
  // QA review: a free-text correction (e.g. termination_for_cause_conditions) is often
  // multi-sentence — a single-line <input> was awkward to review/edit; use a textarea
  // consistently with the object branch above instead.
  return (
    <textarea
      value={value}
      onChange={(event) => onChange(event.target.value)}
      disabled={disabled}
      rows={3}
      className={INPUT_CLASSES}
    />
  );
}

/**
 * CON-005/BR-CON-003's human confirmation flow — the one genuinely new interaction in this
 * epic. For every field `needsConfirmationPaths` names, the reviewer sees the AI's
 * original value *and* its confidence (persona: "Evidence UX" — a decision without the
 * evidence that produced it isn't defensible), then chooses per field, not in bulk,
 * between accepting it as-is or typing a correction — bulk accept-all would defeat the
 * point of a confidence gate that exists specifically to force a human look at *these*
 * fields individually.
 *
 * Every accepted-or-corrected field is stamped `human_confirmed` server-side either way
 * (`apply_confirmation`), and a corrected one additionally `human_corrected` — this UI
 * mirrors that distinction after the fact (`ExtractedDataView`'s "Confirmed"/"Corrected"
 * badges) so a later viewer can tell an AI-accepted value from a human-overridden one.
 */
export function ConfirmationForm({
  contractId,
  versionId,
  fields,
  needsConfirmationPaths,
  canUpdate,
}: ConfirmationFormProps) {
  const router = useRouter();
  const i18n = useI18n();
  const { t, plural, locale } = i18n;

  const entries = useMemo(
    () =>
      needsConfirmationPaths
        .map((path) => ({ path, leaf: getLeafAtPath(fields, path) }))
        .filter((entry): entry is { path: string; leaf: ExtractedLeaf } => Boolean(entry.leaf)),
    [fields, needsConfirmationPaths],
  );

  const [fieldStates, setFieldStates] = useState<Record<string, FieldState>>(() =>
    Object.fromEntries(
      entries.map(({ path, leaf }) => [
        path,
        { mode: "accept" as FieldMode, raw: initialRawValue(leaf.value, expectedTypeForPath(path)) },
      ]),
    ),
  );
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<FormErrorState>(null);

  function updateField(path: string, patch: Partial<FieldState>) {
    setFieldStates((prev) => ({ ...prev, [path]: { ...prev[path], ...patch } }));
  }

  async function submitCorrections(corrections: Record<string, unknown>) {
    setSubmitting(true);
    setError(null);
    try {
      const response = await fetch(`/api/contracts/${contractId}/versions/${versionId}/confirm`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ corrections }),
      });

      if (response.ok) {
        router.refresh();
        return;
      }

      const body = (await response.json().catch(() => null)) as { detail?: string } | null;
      if (response.status === 409) {
        setError({
          title: t("contracts.confirm.alreadyTitle"),
          body: body?.detail ?? t("contracts.confirm.alreadyBody"),
        });
      } else if (response.status === 403) {
        setError({
          title: t("contracts.confirm.forbiddenTitle"),
          body: t("contracts.confirm.forbiddenBody"),
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

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    const corrections: Record<string, unknown> = {};
    for (const { path } of entries) {
      const state = fieldStates[path];
      if (state.mode !== "correct") continue;
      const parsed = parseCorrectionValue(expectedTypeForPath(path), state.raw, i18n);
      if (!parsed.ok) {
        setError({
          title: t("contracts.confirm.checkCorrectionsTitle"),
          body: t("contracts.confirm.checkCorrectionsBody", {
            field: formatFieldPath(path, i18n),
            error: parsed.error,
          }),
        });
        return;
      }
      corrections[path] = parsed.value;
    }

    await submitCorrections(corrections);
  }

  // Edge case confirmed live (2026-09-30): `needs_confirmation` can be reached with zero
  // resolvable `entries` -- `min_confidence([]) === 0.0` (`extracted_data.py`'s own
  // docstring: "no fields at all is treated as the least-confident case"), so a document
  // the AI extracted *nothing* from still gates on confirmation even though there is
  // nothing field-level to review. `POST .../confirm` accepts `{}` corrections
  // unconditionally once the version is in this status, so the fix is a single
  // acknowledgement action rather than silently rendering nothing (which is what this
  // component did before this was caught in manual testing).
  if (entries.length === 0) {
    if (!canUpdate) {
      return (
        <Alert tone="warning" title={t("contracts.confirm.needsTitle")}>
          {t("contracts.confirm.noFieldsReadOnly")}
        </Alert>
      );
    }
    return (
      <section className="space-y-3 rounded-lg border border-warning-border bg-warning-surface p-4">
        <div className="flex items-center gap-2">
          <ShieldAlert className="size-4 text-warning" aria-hidden="true" />
          <h2 className="text-sm font-semibold text-foreground">{t("contracts.confirm.needsTitle")}</h2>
        </div>
        <p className="text-sm text-foreground-muted">
          {t("contracts.confirm.noFieldsBody")}
        </p>
        {error && (
          <Alert tone="danger" title={error.title}>
            {error.body}
          </Alert>
        )}
        <Button type="button" loading={submitting} onClick={() => submitCorrections({})}>
          <CheckCircle2 className="size-4" aria-hidden="true" />
          {submitting ? t("contracts.confirm.submitting") : t("contracts.confirm.submit")}
        </Button>
      </section>
    );
  }

  if (!canUpdate) {
    return (
      <section className="space-y-3 rounded-lg border border-warning-border bg-warning-surface p-4">
        <div className="flex items-center gap-2">
          <ShieldAlert className="size-4 text-warning" aria-hidden="true" />
          <h2 className="text-sm font-semibold text-foreground">
            {plural("contracts.confirm.readOnlyTitle", entries.length)}
          </h2>
        </div>
        <p className="text-sm text-foreground-muted">
          {t("contracts.confirm.readOnlyBody")}
        </p>
        <ul className="space-y-2">
          {entries.map(({ path, leaf }) => (
            <li key={path} className="rounded-md border border-border bg-surface p-3 text-sm">
              <p className="font-medium text-foreground">{formatFieldPath(path, i18n)}</p>
              <p className="mt-0.5 text-foreground-muted">
                {t("contracts.confirm.aiExtracted")}{" "}
                <span className="text-foreground">{describeValue(leaf.value, i18n)}</span> ·{" "}
                {t("contracts.confirm.confidenceInline", { confidence: formatConfidence(leaf.confidence, locale) })}
              </p>
            </li>
          ))}
        </ul>
      </section>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4 rounded-lg border border-warning-border bg-warning-surface p-4">
      <div className="flex items-center gap-2">
        <ShieldAlert className="size-4 text-warning" aria-hidden="true" />
        <h2 className="text-sm font-semibold text-foreground">
          {plural("contracts.confirm.formTitle", entries.length)}
        </h2>
      </div>
      <p className="text-sm text-foreground-muted">
        {t("contracts.confirm.formBody")}
      </p>

      {error && (
        <Alert tone="danger" title={error.title}>
          {error.body}
        </Alert>
      )}

      <ul className="space-y-3">
        {entries.map(({ path, leaf }) => {
          const state = fieldStates[path];
          return (
            <li key={path} className="space-y-3 rounded-md border border-border bg-surface p-3">
              <div>
                <p className="text-sm font-semibold text-foreground">{formatFieldPath(path, i18n)}</p>
                <p className="mt-0.5 flex flex-wrap items-center gap-2 text-xs text-foreground-muted">
                  <span>
                    {t("contracts.confirm.aiExtracted")}{" "}
                    <span className="font-medium text-foreground">{describeValue(leaf.value, i18n)}</span>
                  </span>
                  <Badge tone="warning">
                    {t("contracts.confirm.confidenceInline", { confidence: formatConfidence(leaf.confidence, locale) })}
                  </Badge>
                  <span>{t("contracts.confirm.page", { page: leaf.provenance.page })}</span>
                </p>
              </div>

              <div className="space-y-2">
                <label className="flex items-center gap-2 text-sm text-foreground">
                  <input
                    type="radio"
                    name={`mode-${path}`}
                    checked={state.mode === "accept"}
                    onChange={() => updateField(path, { mode: "accept" })}
                    disabled={submitting}
                  />
                  {t("contracts.confirm.accept")}
                </label>
                <label className="flex items-center gap-2 text-sm text-foreground">
                  <input
                    type="radio"
                    name={`mode-${path}`}
                    checked={state.mode === "correct"}
                    onChange={() => updateField(path, { mode: "correct" })}
                    disabled={submitting}
                  />
                  {t("contracts.confirm.correct")}
                </label>
                {state.mode === "correct" && (
                  <div className="pl-6">
                    <CorrectionInput
                      type={expectedTypeForPath(path)}
                      value={state.raw}
                      onChange={(raw) => updateField(path, { raw })}
                      disabled={submitting}
                    />
                  </div>
                )}
              </div>
            </li>
          );
        })}
      </ul>

      <Button type="submit" loading={submitting}>
        <CheckCircle2 className="size-4" aria-hidden="true" />
        {submitting ? t("contracts.confirm.submitting") : t("contracts.confirm.submit")}
      </Button>
    </form>
  );
}
