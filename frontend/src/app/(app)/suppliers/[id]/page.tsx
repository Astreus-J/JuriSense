import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft } from "lucide-react";

import { Alert } from "@/components/ui/Alert";
import { SupplierCheckHistory } from "@/components/suppliers/SupplierCheckHistory";
import { SupplierDetailActions } from "@/components/suppliers/SupplierDetailActions";
import { SupplierProfileCard } from "@/components/suppliers/SupplierProfileCard";
import { SupplierStatusBadge } from "@/components/suppliers/SupplierStatusBadge";
import { ApiError } from "@/lib/auth/backend";
import { readAccessToken } from "@/lib/auth/cookies";
import { requireSession } from "@/lib/auth/session";
import { getSupplier, getSupplierProfile, listSupplierChecks } from "@/lib/suppliers/backend";
import { getSupplierPermissions } from "@/lib/suppliers/permissions";

export const metadata: Metadata = { title: "Supplier — JuriSense Gate" };

interface SupplierDetailPageProps {
  // Next 16: `params` is a Promise (see `node_modules/next/dist/docs/01-app/
  // 03-api-reference/03-file-conventions/page.md`).
  params: Promise<{ id: string }>;
}

export default async function SupplierDetailPage({ params }: SupplierDetailPageProps) {
  const user = await requireSession();
  const { id } = await params;
  const accessToken = (await readAccessToken())!;
  const permissions = getSupplierPermissions(user.role);

  let supplier;
  try {
    supplier = await getSupplier(accessToken, id);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    if (error instanceof ApiError && error.status === 403) {
      return (
        <div className="space-y-6">
          <BackLink />
          <Alert tone="danger" title="You don't have access to this supplier.">
            Ask an administrator to grant you the &quot;suppliers&quot; read permission for
            this organization.
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
    <div className="space-y-8">
      <BackLink />

      {profile?.sanctionsHit && (
        <Alert tone="danger" title="Sanctions hit detected">
          This supplier matched an entry on a sanctions or watch list during its most recent
          verification. Do not approve it until Compliance has reviewed the match below.
        </Alert>
      )}

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-2xl font-semibold tracking-tight text-foreground">
              {supplier.legalName}
            </h1>
            <SupplierStatusBadge status={supplier.status} />
          </div>
          <p className="mt-1 text-sm text-foreground-muted">
            Tax ID {supplier.taxId} · {supplier.jurisdiction}
          </p>
        </div>

        <SupplierDetailActions supplier={supplier} canUpdate={permissions.canUpdate} />
      </div>

      <SupplierProfileCard profile={profile} />

      <SupplierCheckHistory checks={checks} />
    </div>
  );
}

function BackLink() {
  return (
    <Link
      href="/suppliers"
      className="inline-flex items-center gap-1 text-sm font-medium text-foreground-muted hover:text-foreground"
    >
      <ArrowLeft className="size-4" aria-hidden="true" />
      Back to suppliers
    </Link>
  );
}
