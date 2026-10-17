import { Alert } from "@/components/ui/Alert";
import { PageHeader } from "@/components/ui/PageHeader";
import { UploadContractForm } from "@/components/contracts/UploadContractForm";
import { ApiError } from "@/lib/auth/backend";
import { readAccessToken } from "@/lib/auth/cookies";
import { requireSession } from "@/lib/auth/session";
import { listContracts } from "@/lib/contracts/backend";
import { getI18n, pageTitle } from "@/lib/i18n/server";
import { listSuppliers } from "@/lib/suppliers/backend";

export const generateMetadata = pageTitle("meta.contractNew");

interface NewContractPageProps {
  // Next 16: `searchParams` is a Promise.
  searchParams: Promise<{ contractId?: string }>;
}

/**
 * Scope call (no ticket owns this screen, same situation `suppliers/new` documents for
 * its own form): `POST /contracts/upload` is the only way to get a contract into the
 * system at all, so this route exists to make CON-001/CON-002 usable end to end rather
 * than leaving Contract Intelligence with no entry point.
 *
 * No role gate beyond authentication, for the same reason `suppliers/new` has none: a
 * role's default `create` permission (`getContractPermissions`) is only a UI hint a
 * per-user override can widen, so this page stays reachable and lets the real 403 from
 * `POST /api/contracts/upload` (surfaced by `UploadContractForm`) be authoritative — the
 * list/detail pages already hide the "Upload contract" entry points for roles the default
 * grid says can't create.
 */
export default async function NewContractPage({ searchParams }: NewContractPageProps) {
  await requireSession();
  const { t } = await getI18n();
  const { contractId } = await searchParams;
  const accessToken = (await readAccessToken())!;

  // Both lists are needed regardless of which flow the user ends up picking (the radio
  // choice is client-side), and both are cheap, org-scoped GETs — fetched together rather
  // than gating one behind the other's result.
  //
  // QA review (2026-09-30): unlike contracts/page.tsx, this page had no 403 handling for
  // these fetches at all -- a per-user override narrowing someone's read access below
  // this page's own no-gate design (see docstring above) would throw into the generic
  // error boundary instead of an actionable message. Mirrors the list page's pattern.
  let suppliers: Awaited<ReturnType<typeof listSuppliers>> = [];
  let contracts: Awaited<ReturnType<typeof listContracts>> = [];
  let forbidden = false;
  try {
    [suppliers, contracts] = await Promise.all([
      listSuppliers(accessToken),
      listContracts(accessToken),
    ]);
  } catch (error) {
    if (error instanceof ApiError && error.status === 403) {
      forbidden = true;
    } else {
      throw error;
    }
  }

  const breadcrumbs = [
    { label: t("nav.contracts"), href: "/contracts" },
    { label: t("contracts.new.breadcrumb") },
  ];

  if (forbidden) {
    return (
      <div className="max-w-lg space-y-5">
        <PageHeader title={t("contracts.new.title")} breadcrumbs={breadcrumbs} />
        <Alert tone="danger" title={t("contracts.new.noAccessTitle")}>
          {t("contracts.new.noAccessBody")}
        </Alert>
      </div>
    );
  }

  return (
    <div className="max-w-lg space-y-5">
      <PageHeader
        breadcrumbs={breadcrumbs}
        title={t("contracts.new.title")}
        description={t("contracts.new.description")}
      />

      <UploadContractForm
        suppliers={suppliers.map((supplier) => ({ id: supplier.id, legalName: supplier.legalName }))}
        contracts={contracts.map((contract) => ({
          id: contract.id,
          title: contract.title,
          supplierId: contract.supplierId,
        }))}
        initialContractId={contractId}
      />
    </div>
  );
}
