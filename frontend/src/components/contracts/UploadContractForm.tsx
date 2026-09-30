"use client";

import { useId, useState } from "react";
import type { ChangeEvent, FormEvent } from "react";
import { useRouter } from "next/navigation";

import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { cn } from "@/lib/cn";

const SELECT_CLASSES =
  "w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground shadow-sm " +
  "focus:outline-none focus:ring-2 focus:ring-focus-ring focus:border-transparent disabled:cursor-not-allowed disabled:opacity-60";

type UploadMode = "new" | "version";
type FormErrorState = { title: string; body?: string } | null;

export interface SupplierOption {
  id: string;
  legalName: string;
}

export interface ContractOption {
  id: string;
  title: string;
  supplierId: string;
}

interface UploadContractFormProps {
  suppliers: SupplierOption[];
  contracts: ContractOption[];
  /** Pre-selects "Add a new version" for this contract when arriving from its detail page
   * (`/contracts/new?contractId=...`) — see that link's own comment for why. */
  initialContractId?: string;
}

/**
 * Both of `POST /contracts/upload`'s two flows in one form, switched by a single radio
 * choice — mirrors the fact that the backend itself models them as one endpoint
 * (`contract_service.upload_contract_version`'s own docstring: "two Plane stories... are
 * one pipeline in practice"). Deliberately does *not* let "add a new version" also expose
 * an independent supplier picker: the supplier is derived from the chosen contract, which
 * both removes a field and prevents the exact 409 `SupplierMismatchError` a free-form
 * picker would otherwise regularly trigger (persona: "prevent mistakes" beats "surface
 * every possible input").
 *
 * A dedicated route rather than a modal, for the same reason `suppliers/new` is (persona:
 * "do not over-design" — this needs its own URL/back-button behavior and the upload can
 * take a few seconds, not a lightweight action to hide behind a modal's focus trap).
 */
export function UploadContractForm({ suppliers, contracts, initialContractId }: UploadContractFormProps) {
  const router = useRouter();
  const fileInputId = useId();

  const [mode, setMode] = useState<UploadMode>(initialContractId ? "version" : "new");
  const [contractId, setContractId] = useState(initialContractId ?? "");
  const [supplierId, setSupplierId] = useState("");
  const [title, setTitle] = useState("");
  const [contractType, setContractType] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<FormErrorState>(null);

  const selectedContract = contracts.find((contract) => contract.id === contractId);

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    setFile(event.target.files?.[0] ?? null);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) {
      setError({ title: "Choose a file", body: "A contract document is required." });
      return;
    }
    if (mode === "version" && !contractId) {
      setError({ title: "Choose a contract", body: "Select which contract this version belongs to." });
      return;
    }
    if (mode === "new" && !supplierId) {
      setError({ title: "Choose a supplier", body: "Select which supplier this contract is with." });
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.set("file", file);
      if (mode === "version") {
        formData.set("contractId", contractId);
        formData.set("supplierId", selectedContract!.supplierId);
      } else {
        formData.set("supplierId", supplierId);
        formData.set("title", title);
        formData.set("contractType", contractType);
      }

      const response = await fetch("/api/contracts/upload", { method: "POST", body: formData });

      if (response.ok) {
        const version = (await response.json()) as { contractId: string };
        router.push(`/contracts/${version.contractId}`);
        router.refresh();
        return;
      }

      const body = (await response.json().catch(() => null)) as { detail?: string } | null;
      if (response.status === 409) {
        setError({
          title: "Conflict",
          body: body?.detail ?? "This upload conflicts with the contract's current state.",
        });
      } else if (response.status === 403) {
        setError({
          title: "You can't upload contracts",
          body: 'Ask an administrator to grant you the "contracts" create permission.',
        });
      } else if (response.status === 422 || response.status === 400) {
        setError({ title: "Check the form", body: body?.detail ?? "Some fields are invalid." });
      } else if (response.status === 413) {
        setError({ title: "File too large", body: body?.detail ?? "This file exceeds the 25 MB limit." });
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
    <form onSubmit={handleSubmit} noValidate className="space-y-6">
      {error && (
        <Alert tone="danger" title={error.title}>
          {error.body}
        </Alert>
      )}

      <fieldset className="space-y-2">
        <legend className="text-sm font-medium text-foreground">What are you uploading?</legend>
        <div className="space-y-2">
          <label className="flex cursor-pointer items-start gap-2 rounded-md border border-border p-3 text-sm has-[:checked]:border-primary has-[:checked]:bg-surface-muted">
            <input
              type="radio"
              name="mode"
              value="new"
              checked={mode === "new"}
              onChange={() => setMode("new")}
              disabled={submitting}
              className="mt-0.5"
            />
            <span>
              <span className="block font-medium text-foreground">A new contract</span>
              <span className="block text-foreground-muted">
                The first version of an agreement JuriSense hasn&apos;t seen before.
              </span>
            </span>
          </label>
          <label className="flex cursor-pointer items-start gap-2 rounded-md border border-border p-3 text-sm has-[:checked]:border-primary has-[:checked]:bg-surface-muted">
            <input
              type="radio"
              name="mode"
              value="version"
              checked={mode === "version"}
              onChange={() => setMode("version")}
              disabled={submitting || contracts.length === 0}
              className="mt-0.5"
            />
            <span>
              <span className="block font-medium text-foreground">
                A new version of an existing contract
              </span>
              <span className="block text-foreground-muted">
                {contracts.length === 0
                  ? "No existing contracts to add a version to yet."
                  : "A new negotiation round, amendment, or renewal of a contract already on file."}
              </span>
            </span>
          </label>
        </div>
      </fieldset>

      {mode === "new" ? (
        <div className="space-y-5">
          <div className="space-y-1.5">
            <label htmlFor="upload-supplier" className="block text-sm font-medium text-foreground">
              Supplier
            </label>
            <select
              id="upload-supplier"
              value={supplierId}
              onChange={(event) => setSupplierId(event.target.value)}
              disabled={submitting}
              required
              className={SELECT_CLASSES}
            >
              <option value="">Select a supplier…</option>
              {suppliers.map((supplier) => (
                <option key={supplier.id} value={supplier.id}>
                  {supplier.legalName}
                </option>
              ))}
            </select>
            {suppliers.length === 0 && (
              <p className="text-xs text-foreground-muted">
                No suppliers registered yet — register one first.
              </p>
            )}
          </div>

          <Field
            label="Title"
            name="title"
            required
            placeholder="e.g. Master Services Agreement — CloudVendor"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            disabled={submitting}
          />

          <Field
            label="Contract type"
            name="contractType"
            required
            maxLength={50}
            hint="e.g. MSA, NDA, DPA, SOW."
            value={contractType}
            onChange={(event) => setContractType(event.target.value)}
            disabled={submitting}
          />
        </div>
      ) : (
        <div className="space-y-1.5">
          <label htmlFor="upload-contract" className="block text-sm font-medium text-foreground">
            Contract
          </label>
          <select
            id="upload-contract"
            value={contractId}
            onChange={(event) => setContractId(event.target.value)}
            disabled={submitting}
            required
            className={SELECT_CLASSES}
          >
            <option value="">Select a contract…</option>
            {contracts.map((contract) => (
              <option key={contract.id} value={contract.id}>
                {contract.title}
              </option>
            ))}
          </select>
        </div>
      )}

      <div className="space-y-1.5">
        <label htmlFor={fileInputId} className="block text-sm font-medium text-foreground">
          Contract document
        </label>
        <input
          id={fileInputId}
          type="file"
          accept=".pdf,.docx,.txt"
          onChange={handleFileChange}
          disabled={submitting}
          required
          className={cn(
            "block w-full text-sm text-foreground-muted file:mr-3 file:rounded-md file:border-0 file:bg-primary",
            "file:px-3 file:py-2 file:text-sm file:font-medium file:text-primary-foreground hover:file:bg-primary-hover",
          )}
        />
        <p className="text-xs text-foreground-muted">PDF, DOCX, or TXT — up to 25 MB.</p>
      </div>

      <Button type="submit" loading={submitting} className="w-full">
        {submitting ? "Uploading…" : "Upload contract"}
      </Button>
    </form>
  );
}
