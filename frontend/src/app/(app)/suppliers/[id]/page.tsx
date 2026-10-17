import { StatusBadge } from "@/components/shared/StatusBadge";
import { notFound } from "next/navigation";

import { Alert } from "@/components/ui/Alert";
import { PageHeader } from "@/components/ui/PageHeader";
import { SupplierCheckHistory } from "@/components/suppliers/SupplierCheckHistory";
import { SupplierDetailActions } from "@/components/suppliers/SupplierDetailActions";
import { SupplierProfileCard } from "@/components/suppliers/SupplierProfileCard";
import { ApiError } from "@/lib/auth/backend";
import { readAccessToken } from "@/lib/auth/cookies";
import { requireSession } from "@/lib/auth/session";
import { getI18n, pageTitle } from "@/lib/i18n/server";
import { getSupplier, getSupplierProfile, listSupplierChecks } from "@/lib/suppliers/backend";
import { getSupplierPermissions } from "@/lib/suppliers/permissions";

export const generateMetadata = pageTitle("meta.supplier");

interface SupplierDetailPageProps {
  // Next 16: `params` is a Promise (see `node_modules/next/dist/docs/01-app/
  // 03-api-reference/03-file-conventions/page.md`).
  params: Promise<{ id: string }>;
}

export default async function SupplierDetailPage({ params }: SupplierDetailPageProps) {
  const user = await requireSession();
  const { t } = await getI18n();
  const breadcrumbs = [
    { label: t("nav.suppliers"), href: "/suppliers" },
    { label: t("suppliers.detail.breadcrumb") },
  ];
  const { id } = await params;
  const accessToken = (await readAccessToken())!;
  const permissions = getSupplierPermissions(user.role);

  let supplier;
  try {
    supplier = await getSupplier(accessToken, id);
  } catch (error) {
    // A malformed id (not a UUID) is treated the same as "no such supplier" -- there's no
    // useful distinction to surface to the user, and it avoids routing an invalid-input
    // case through the generic error boundary instead of the expected not-found page.
    if (error instanceof ApiError && (error.status === 404 || error.status === 400)) notFound();
    if (error instanceof ApiError && error.status === 403) {
      return (
        <div className="space-y-5">
          <PageHeader title={t("suppliers.detail.breadcrumb")} breadcrumbs={breadcrumbs} />
          <Alert tone="danger" title={t("suppliers.detail.noAccessTitle")}>
            {t("suppliers.detail.noAccessBody")}
          </Alert>
        </div>
      );
    }
    throw error;
  }

  const [profile, checks] = await Promise.all([
    getSupplierProfile(accessToken, id),
    listSupplierChecks(accessToken, id),
  ]);

  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumbs={[breadcrumbs[0], { label: supplier.legalName }]}
        title={supplier.legalName}
        meta={
          <>
            <StatusBadge kind="supplier" value={supplier.status} />
            <span className="text-sm text-foreground-muted">
              {t("suppliers.detail.taxId")} <span className="font-mono text-xs tabular-nums text-foreground">{supplier.taxId}</span>
              {" · "}
              {supplier.jurisdiction}
            </span>
          </>
        }
        // #142 code review (2026-10-14): `key={supplier.id}` forces React to unmount
        // and remount this component on navigation between two different suppliers --
        // without it, the client component instance (and its in-flight recheck-polling
        // state/interval) survives across the navigation and keeps polling the PREVIOUS
        // supplier's checks, misattributing that result to whichever supplier is now
        // displayed.
        actions={
          <SupplierDetailActions
            key={supplier.id}
            supplier={supplier}
            canUpdate={permissions.canUpdate}
          />
        }
      />

      {profile?.sanctionsHit && (
        <Alert tone="danger" title={t("suppliers.detail.sanctionsTitle")}>
          {t("suppliers.detail.sanctionsBody")}
        </Alert>
      )}

      <SupplierProfileCard profile={profile} />

      <SupplierCheckHistory checks={checks} />
    </div>
  );
}
