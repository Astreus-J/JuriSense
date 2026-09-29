"use client";

import { useState } from "react";
import type { FormEvent } from "react";
import { useRouter } from "next/navigation";

import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";

type FormErrorState = { title: string; body?: string } | null;

/**
 * EPIC-2 (#29) requires "A Procurement-role user registers a Supplier with a CNPJ" to work
 * end to end via the UI, and story #32 owns the only Suppliers screens — see the Plane
 * comment on #32 for the explicit scope call to include this form here rather than leaving
 * it to a separate, unowned story.
 */
export function CreateSupplierForm() {
  const router = useRouter();
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
          title: "Already registered",
          body: body?.detail ?? "A supplier with this tax ID is already registered.",
        });
      } else if (response.status === 403) {
        setError({
          title: "You can't register suppliers",
          body: 'Ask an administrator to grant you the "suppliers" create permission.',
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
        label="Legal name"
        name="legalName"
        autoComplete="organization"
        required
        value={legalName}
        onChange={(event) => setLegalName(event.target.value)}
        disabled={submitting}
      />

      <Field
        label="Tax ID"
        name="taxId"
        required
        hint="CNPJ, or the equivalent registration number for the supplier's jurisdiction."
        value={taxId}
        onChange={(event) => setTaxId(event.target.value)}
        disabled={submitting}
      />

      <Field
        label="Jurisdiction"
        name="jurisdiction"
        required
        maxLength={2}
        hint="Two-letter country code, e.g. BR."
        value={jurisdiction}
        onChange={(event) => setJurisdiction(event.target.value.toUpperCase())}
        disabled={submitting}
      />

      <Button type="submit" loading={submitting} className="w-full">
        {submitting ? "Registering…" : "Register supplier"}
      </Button>
    </form>
  );
}
