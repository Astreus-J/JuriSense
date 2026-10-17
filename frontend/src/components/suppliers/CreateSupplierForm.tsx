"use client";

import { useState } from "react";
import type { FormEvent } from "react";
import { useRouter } from "next/navigation";

import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { useI18n } from "@/lib/i18n/client";

type FormErrorState = { title: string; body?: string } | null;

/**
 * EPIC-2 (#29) requires "A Procurement-role user registers a Supplier with a CNPJ" to work
 * end to end via the UI, and story #32 owns the only Suppliers screens — see the Plane
 * comment on #32 for the explicit scope call to include this form here rather than leaving
 * it to a separate, unowned story.
 */
export function CreateSupplierForm() {
  const router = useRouter();
  const { t } = useI18n();
  const [legalName, setLegalName] = useState("");
  const [taxId, setTaxId] = useState("");
  const [jurisdiction, setJurisdiction] = useState("BR");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<FormErrorState>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      const response = await fetch("/api/suppliers", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ legalName, taxId, jurisdiction }),
      });

      if (response.ok) {
        const supplier = (await response.json()) as { id: string };
        router.push(`/suppliers/${supplier.id}`);
        router.refresh();
        return;
      }

      const body = (await response.json().catch(() => null)) as { detail?: string } | null;
      if (response.status === 409) {
        setError({
          title: t("suppliers.form.alreadyTitle"),
          body: body?.detail ?? t("suppliers.form.alreadyBody"),
        });
      } else if (response.status === 403) {
        setError({
          title: t("suppliers.form.forbiddenTitle"),
          body: t("suppliers.form.forbiddenBody"),
        });
      } else if (response.status === 400) {
        setError({ title: t("suppliers.form.checkTitle"), body: body?.detail ?? t("suppliers.form.checkBody") });
      } else {
        setError({ title: t("errors.somethingWentWrong"), body: t("errors.tryAgainShortly") });
      }
    } catch {
      setError({ title: t("errors.couldNotReachServer"), body: t("errors.tryAgain") });
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
        label={t("suppliers.form.legalName")}
        name="legalName"
        autoComplete="organization"
        required
        value={legalName}
        onChange={(event) => setLegalName(event.target.value)}
        disabled={submitting}
      />

      <Field
        label={t("suppliers.form.taxId")}
        name="taxId"
        required
        hint={t("suppliers.form.taxIdHint")}
        value={taxId}
        onChange={(event) => setTaxId(event.target.value)}
        disabled={submitting}
      />

      <Field
        label={t("suppliers.form.jurisdiction")}
        name="jurisdiction"
        required
        maxLength={2}
        hint={t("suppliers.form.jurisdictionHint")}
        value={jurisdiction}
        onChange={(event) => setJurisdiction(event.target.value.toUpperCase())}
        disabled={submitting}
      />

      <Button type="submit" loading={submitting}>
        {submitting ? t("suppliers.form.submitting") : t("suppliers.form.submit")}
      </Button>
    </form>
  );
}
