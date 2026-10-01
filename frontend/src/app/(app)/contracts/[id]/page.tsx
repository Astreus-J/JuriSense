import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft, Loader2, Plus } from "lucide-react";

import { Alert } from "@/components/ui/Alert";
import { buttonClasses } from "@/components/ui/Button";
import { ClauseList } from "@/components/contracts/ClauseList";
import { ComplianceReviewHistory } from "@/components/compliance/ComplianceReviewHistory";
import { ConfirmationForm } from "@/components/contracts/ConfirmationForm";
import { ContractStatusBadge } from "@/components/contracts/ContractStatusBadge";
import { ContractVersionList } from "@/components/contracts/ContractVersionList";
import { ContractVersionStatusBadge } from "@/components/contracts/ContractVersionStatusBadge";
import { ExtractedDataView } from "@/components/contracts/ExtractedDataView";
import { TriggerComplianceReviewButton } from "@/components/compliance/TriggerComplianceReviewButton";
import { ApiError } from "@/lib/auth/backend";
import { readAccessToken } from "@/lib/auth/cookies";
import { requireSession } from "@/lib/auth/session";
import { listComplianceReviews } from "@/lib/compliance/backend";
import { getCompliancePermissions } from "@/lib/compliance/permissions";
import {
  getContract,
  getContractVersion,
  listContractVersionClauses,
  listContractVersions,
} from "@/lib/contracts/backend";
import { getContractPermissions } from "@/lib/contracts/permissions";
import { formatConfidence, formatDateTime } from "@/lib/format";
import { getSupplier } from "@/lib/suppliers/backend";
import type { ContractFields, ContractVersion } from "@/lib/contracts/types";

export const metadata: Metadata = { title: "Contract — JuriSense Gate" };

interface ContractDetailPageProps {
  // Next 16: `params`/`searchParams` are Promises.
  params: Promise<{ id: string }>;
  searchParams: Promise<{ version?: string }>;
}

export default async function ContractDetailPage({ params, searchParams }: ContractDetailPageProps) {
  const user = await requireSession();
  const { id } = await params;
  const { version: versionParam } = await searchParams;
  const accessToken = (await readAccessToken())!;
  const permissions = getContractPermissions(user.role);
  const compliancePermissions = getCompliancePermissions(user.role);

  let contract;
  try {
    contract = await getContract(accessToken, id);
  } catch (error) {
    // A malformed id is treated the same as "no such contract" — see
    // `suppliers/[id]/page.tsx`'s identical note.
    if (error instanceof ApiError && (error.status === 404 || error.status === 400)) notFound();
    if (error instanceof ApiError && error.status === 403) {
      return (
        <div className="space-y-6">
          <BackLink />
          <Alert tone="danger" title="You don't have access to this contract.">
            Ask an administrator to grant you the &quot;contracts&quot; read permission for
            this organization.
          </Alert>
        </div>
      );
    }
    throw error;
  }

  const versions = await listContractVersions(accessToken, id);
  if (versions.length === 0) {
    // A Contract is only ever created together with its first Version
    // (`contract_service.upload_contract_version`) — this is a defensive branch for an
    // invariant that should never actually break, not an expected empty state.
    return (
      <div className="space-y-6">
        <BackLink />
        <Alert tone="warning" title="This contract has no versions yet.">
          This shouldn&apos;t normally happen — contact support if it persists.
        </Alert>
      </div>
    );
  }

  const currentVersionNumber = Math.max(...versions.map((v) => v.versionNumber));
  const requestedVersionNumber = versionParam ? Number(versionParam) : currentVersionNumber;
  const selectedSummary =
    versions.find((v) => v.versionNumber === requestedVersionNumber) ??
    versions.find((v) => v.versionNumber === currentVersionNumber)!;

  const [version, clauses, supplierName, complianceReviews] = await Promise.all([
    getContractVersion(accessToken, id, selectedSummary.id),
    listContractVersionClauses(accessToken, id, selectedSummary.id),
    // Best-effort: every default role with Contracts read also has Suppliers read, but a
    // per-user override could narrow that — degrade to the raw id rather than fail the page.
    getSupplier(accessToken, contract.supplierId)
      .then((supplier) => supplier.legalName)
      .catch(() => null),
    // Same best-effort reasoning as `supplierName` above, for `compliance_reviews` instead of
    // `suppliers` — the review-history list is a nice-to-have on this page, not load-bearing,
    // so a narrowed per-user override degrades to "no history shown" rather than a 500.
    compliancePermissions.canRead
      ? listComplianceReviews(accessToken, selectedSummary.id).catch(() => [])
      : Promise.resolve([]),
  ]);

  const fields = (version.extractedData as { fields?: ContractFields }).fields ?? {};

  return (
    <div className="space-y-6">
      <BackLink />

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-2xl font-semibold tracking-tight text-foreground">{contract.title}</h1>
            <ContractStatusBadge status={contract.status} />
          </div>
          <p className="mt-1 text-sm text-foreground-muted">
            {contract.contractType} ·{" "}
            {supplierName ? (
              <Link href={`/suppliers/${contract.supplierId}`} className="hover:underline">
                {supplierName}
              </Link>
            ) : (
              "Unknown supplier"
            )}{" "}
            · Created {formatDateTime(contract.createdAt)}
          </p>
        </div>

        {permissions.canCreate && (
          <Link
            href={`/contracts/new?contractId=${contract.id}`}
            className={buttonClasses("secondary")}
          >
            <Plus className="size-4" aria-hidden="true" />
            Upload new version
          </Link>
        )}
      </div>

      <div className="grid gap-6 lg:grid-cols-[240px_1fr]">
        <ContractVersionList contractId={contract.id} versions={versions} selectedVersionId={version.id} />

        <div className="space-y-6">
          <VersionSummary version={version} />

          {compliancePermissions.canCreate && version.status === "analyzed" && (
            <div className="flex justify-end">
              <TriggerComplianceReviewButton
                contractId={contract.id}
                contractVersionId={version.id}
              />
            </div>
          )}

          {complianceReviews.length > 0 && (
            <ComplianceReviewHistory contractId={contract.id} reviews={complianceReviews} />
          )}

          {version.status === "extracted" && (
            <section className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-border bg-surface px-6 py-16 text-center">
              <Loader2 className="size-6 motion-safe:animate-spin text-foreground-muted" aria-hidden="true" />
              <p className="text-sm font-medium text-foreground">Extraction in progress</p>
              <p className="mx-auto max-w-sm text-sm text-foreground-muted">
                JuriSense is reading this document and structuring its key terms. This
                usually takes a minute or two — refresh to check for an update.
              </p>
            </section>
          )}

          {version.status === "extraction_failed" && (
            <Alert tone="danger" title="Extraction failed">
              {version.extractionFailureReason ??
                "AI extraction could not process this document. Try uploading it again."}
            </Alert>
          )}

          {version.status === "needs_confirmation" && (
            <ConfirmationForm
              contractId={contract.id}
              versionId={version.id}
              fields={fields}
              needsConfirmationPaths={version.needsConfirmationPaths}
              canUpdate={permissions.canUpdate}
            />
          )}

          {(version.status === "analyzed" || version.status === "needs_confirmation") && (
            <>
              <ExtractedDataView fields={fields} needsConfirmationPaths={version.needsConfirmationPaths} />
              <ClauseList clauses={clauses} />
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function VersionSummary({ version }: { version: ContractVersion }) {
  return (
    <div className="flex flex-wrap items-center gap-3 rounded-xl border border-border bg-surface p-4">
      <span className="text-sm font-semibold text-foreground">Version {version.versionNumber}</span>
      <ContractVersionStatusBadge status={version.status} />
      {version.extractionConfidence !== null && (
        <span className="text-xs text-foreground-muted">
          Minimum field confidence: {formatConfidence(version.extractionConfidence)}
        </span>
      )}
      <span className="text-xs text-foreground-muted">Uploaded {formatDateTime(version.createdAt)}</span>
    </div>
  );
}

function BackLink() {
  return (
    <Link
      href="/contracts"
      className="inline-flex items-center gap-1 text-sm font-medium text-foreground-muted hover:text-foreground"
    >
      <ArrowLeft className="size-4" aria-hidden="true" />
      Back to contracts
    </Link>
  );
}
