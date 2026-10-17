import { StatusBadge } from "@/components/shared/StatusBadge";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Loader2, Plus } from "lucide-react";

import { Alert } from "@/components/ui/Alert";
import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { buttonClasses } from "@/components/ui/Button";
import { ClauseList } from "@/components/contracts/ClauseList";
import { ComplianceReviewHistory } from "@/components/compliance/ComplianceReviewHistory";
import { ConfirmationForm } from "@/components/contracts/ConfirmationForm";
import { ContractVersionList } from "@/components/contracts/ContractVersionList";
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
import { getI18n, pageTitle } from "@/lib/i18n/server";
import { getSupplier } from "@/lib/suppliers/backend";
import type { Translator } from "@/lib/i18n/translate";
import type { ContractFields, ContractVersion } from "@/lib/contracts/types";

export const generateMetadata = pageTitle("meta.contract");

interface ContractDetailPageProps {
  // Next 16: `params`/`searchParams` are Promises.
  params: Promise<{ id: string }>;
  searchParams: Promise<{ version?: string }>;
}

export default async function ContractDetailPage({ params, searchParams }: ContractDetailPageProps) {
  const user = await requireSession();
  const i18n = await getI18n();
  const { t, locale } = i18n;
  const breadcrumbs = [
    { label: t("nav.contracts"), href: "/contracts" },
    { label: t("contracts.detail.breadcrumb") },
  ];
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
        <div className="space-y-5">
          <PageHeader title={t("contracts.detail.breadcrumb")} breadcrumbs={breadcrumbs} />
          <Alert tone="danger" title={t("contracts.detail.noAccessTitle")}>
            {t("contracts.detail.noAccessBody")}
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
      <div className="space-y-5">
        <PageHeader title={contract.title} breadcrumbs={breadcrumbs} />
        <Alert tone="warning" title={t("contracts.detail.noVersionsTitle")}>
          {t("contracts.detail.noVersionsBody")}
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
      <PageHeader
        breadcrumbs={[breadcrumbs[0], { label: contract.title }]}
        title={contract.title}
        meta={
          <>
            <StatusBadge kind="contract" value={contract.status} />
            <span className="text-sm text-foreground-muted">
              {contract.contractType} ·{" "}
              {supplierName ? (
                <Link
                  href={`/suppliers/${contract.supplierId}`}
                  className="text-foreground hover:underline"
                >
                  {supplierName}
                </Link>
              ) : (
                t("contracts.detail.unknownSupplier")
              )}{" "}
              · {t("contracts.detail.created", { date: formatDateTime(contract.createdAt, locale) })}
            </span>
          </>
        }
        actions={
          permissions.canCreate ? (
            <Link
              href={`/contracts/new?contractId=${contract.id}`}
              className={buttonClasses("secondary")}
            >
              <Plus className="size-4" aria-hidden="true" />
              {t("contracts.detail.uploadVersion")}
            </Link>
          ) : undefined
        }
      />

      <div className="grid gap-8 lg:grid-cols-[200px_minmax(0,1fr)]">
        <ContractVersionList contractId={contract.id} versions={versions} selectedVersionId={version.id} />

        <div className="min-w-0 space-y-6">
          <VersionSummary
            version={version}
            i18n={i18n}
            action={
              compliancePermissions.canCreate && version.status === "analyzed" ? (
                <TriggerComplianceReviewButton
                  contractId={contract.id}
                  contractVersionId={version.id}
                />
              ) : undefined
            }
          />

          {complianceReviews.length > 0 && (
            <ComplianceReviewHistory contractId={contract.id} reviews={complianceReviews} />
          )}

          {version.status === "extracted" && (
            <EmptyState
              icon={Loader2}
              title={t("contracts.detail.extractionInProgressTitle")}
              description={t("contracts.detail.extractionInProgressBody")}
            />
          )}

          {version.status === "extraction_failed" && (
            <Alert tone="danger" title={t("contracts.detail.extractionFailedTitle")}>
              {version.extractionFailureReason ?? t("contracts.detail.extractionFailedDefault")}
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

function VersionSummary({
  version,
  action,
  i18n: { t, locale },
}: {
  version: ContractVersion;
  action?: React.ReactNode;
  i18n: Translator;
}) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2 border-b border-border pb-3">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <h2 className="text-base font-semibold text-foreground">
          {t("contracts.detail.versionHeading", { number: version.versionNumber })}
        </h2>
        <StatusBadge kind="contractVersion" value={version.status} />
        <span className="text-xs text-foreground-muted">
          {t("contracts.detail.uploaded", { date: formatDateTime(version.createdAt, locale) })}
        </span>
        {version.extractionConfidence !== null && (
          <span className="text-xs text-foreground-muted">
            {t("contracts.detail.minConfidence")}{" "}
            <span className="tabular-nums">{formatConfidence(version.extractionConfidence, locale)}</span>
          </span>
        )}
      </div>
      {action}
    </div>
  );
}
