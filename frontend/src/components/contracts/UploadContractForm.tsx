"use client";

import { useId, useState } from "react";
import type { ChangeEvent, FormEvent } from "react";
import { useRouter } from "next/navigation";

import { Alert } from "@/components/ui/Alert";
import { controlClasses } from "@/components/ui/Field";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { cn } from "@/lib/cn";
import { useI18n } from "@/lib/i18n/client";

const SELECT_CLASSES = `w-full ${controlClasses}`;

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
  const { t } = useI18n();
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
      setError({ title: t("contracts.upload.chooseFileTitle"), body: t("contracts.upload.chooseFileBody") });
      return;
    }
    if (mode === "version" && !contractId) {
      setError({
        title: t("contracts.upload.chooseContractTitle"),
        body: t("contracts.upload.chooseContractBody"),
      });
      return;
    }
    if (mode === "new" && !supplierId) {
      setError({
        title: t("contracts.upload.chooseSupplierTitle"),
        body: t("contracts.upload.chooseSupplierBody"),
      });
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
          title: t("contracts.upload.conflictTitle"),
          body: body?.detail ?? t("contracts.upload.conflictBody"),
        });
      } else if (response.status === 403) {
        setError({
          title: t("contracts.upload.forbiddenTitle"),
          body: t("contracts.upload.forbiddenBody"),
        });
      } else if (response.status === 422 || response.status === 400) {
        setError({
          title: t("contracts.upload.checkTitle"),
          body: body?.detail ?? t("contracts.upload.checkBody"),
        });
      } else if (response.status === 413) {
        setError({
          title: t("contracts.upload.tooLargeTitle"),
          body: body?.detail ?? t("contracts.upload.tooLargeBody"),
        });
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
    <form onSubmit={handleSubmit} noValidate className="space-y-6">
      {error && (
        <Alert tone="danger" title={error.title}>
          {error.body}
        </Alert>
      )}

      <fieldset className="space-y-2">
        <legend className="text-sm font-medium text-foreground">{t("contracts.upload.whatTitle")}</legend>
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
              <span className="block font-medium text-foreground">{t("contracts.upload.newTitle")}</span>
              <span className="block text-foreground-muted">
                {t("contracts.upload.newBody")}
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
                {t("contracts.upload.versionTitle")}
              </span>
              <span className="block text-foreground-muted">
                {contracts.length === 0
                  ? t("contracts.upload.versionBodyNone")
                  : t("contracts.upload.versionBody")}
              </span>
            </span>
          </label>
        </div>
      </fieldset>

      {mode === "new" ? (
        <div className="space-y-5">
          <div className="space-y-1.5">
            <label htmlFor="upload-supplier" className="block text-sm font-medium text-foreground">
              {t("contracts.upload.supplier")}
            </label>
            <select
              id="upload-supplier"
              value={supplierId}
              onChange={(event) => setSupplierId(event.target.value)}
              disabled={submitting}
              required
              className={SELECT_CLASSES}
            >
              <option value="">{t("contracts.upload.selectSupplier")}</option>
              {suppliers.map((supplier) => (
                <option key={supplier.id} value={supplier.id}>
                  {supplier.legalName}
                </option>
              ))}
            </select>
            {suppliers.length === 0 && (
              <p className="text-xs text-foreground-muted">
                {t("contracts.upload.noSuppliers")}
              </p>
            )}
          </div>

          <Field
            label={t("contracts.upload.titleLabel")}
            name="title"
            required
            placeholder={t("contracts.upload.titlePlaceholder")}
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            disabled={submitting}
          />

          <Field
            label={t("contracts.upload.contractType")}
            name="contractType"
            required
            maxLength={50}
            hint={t("contracts.upload.contractTypeHint")}
            value={contractType}
            onChange={(event) => setContractType(event.target.value)}
            disabled={submitting}
          />
        </div>
      ) : (
        <div className="space-y-1.5">
          <label htmlFor="upload-contract" className="block text-sm font-medium text-foreground">
            {t("contracts.upload.contract")}
          </label>
          <select
            id="upload-contract"
            value={contractId}
            onChange={(event) => setContractId(event.target.value)}
            disabled={submitting}
            required
            className={SELECT_CLASSES}
          >
            <option value="">{t("contracts.upload.selectContract")}</option>
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
          {t("contracts.upload.document")}
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
        <p className="text-xs text-foreground-muted">{t("contracts.upload.documentHint")}</p>
      </div>

      <Button type="submit" loading={submitting} className="w-full">
        {submitting ? t("contracts.upload.submitting") : t("contracts.upload.submit")}
      </Button>
    </form>
  );
}
