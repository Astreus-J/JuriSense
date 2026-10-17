import Link from "next/link";
import { Plus } from "lucide-react";

import { Alert } from "@/components/ui/Alert";
import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { buttonClasses } from "@/components/ui/Button";
import { StatusFilterTabs } from "@/components/suppliers/StatusFilterTabs";
import { SupplierTable } from "@/components/suppliers/SupplierTable";
import { ApiError } from "@/lib/auth/backend";
import { readAccessToken } from "@/lib/auth/cookies";
import { requireSession } from "@/lib/auth/session";
import { getI18n, pageTitle } from "@/lib/i18n/server";
import { NAV_ITEMS } from "@/lib/navigation/modules";
import { listSuppliers } from "@/lib/suppliers/backend";
import { getSupplierPermissions } from "@/lib/suppliers/permissions";
import { SUPPLIER_STATUSES } from "@/lib/suppliers/types";
import type { SupplierStatus } from "@/lib/suppliers/types";

export const generateMetadata = pageTitle("meta.suppliers");

function isSupplierStatus(value: string): value is SupplierStatus {
  return (SUPPLIER_STATUSES as readonly string[]).includes(value);
}

interface SuppliersPageProps {
  // Next 16: `searchParams` is a Promise (see `node_modules/next/dist/docs/01-app/
  // 03-api-reference/03-file-conventions/page.md`).
  searchParams: Promise<{ status?: string }>;
}

export default async function SuppliersPage({ searchParams }: SuppliersPageProps) {
  const user = await requireSession();
  const { t } = await getI18n();
  const { status } = await searchParams;
  const activeStatus = status && isSupplierStatus(status) ? status : undefined;
  const permissions = getSupplierPermissions(user.role);

  const accessToken = await readAccessToken();
  let suppliers: Awaited<ReturnType<typeof listSuppliers>> = [];
  let forbidden = false;

  try {
    // `requireSession()` above already guarantees a valid token exists; the `!` mirrors
    // the same non-null assumption `getSession()` makes right after its own read.
    suppliers = await listSuppliers(accessToken!, activeStatus);
  } catch (error) {
    if (error instanceof ApiError && error.status === 403) {
      forbidden = true;
    } else {
      // Anything else (5xx, network) is a real failure — let the segment's error.tsx handle it.
      throw error;
    }
  }

  return (
    <div className="space-y-5">
      <PageHeader
        title={t("nav.suppliers")}
        description={t("suppliers.list.description")}
        actions={
          !forbidden && permissions.canCreate ? (
            <Link href="/suppliers/new" className={buttonClasses("primary")}>
              <Plus className="size-4" aria-hidden="true" />
              {t("suppliers.list.register")}
            </Link>
          ) : undefined
        }
      />

      {forbidden ? (
        <Alert tone="danger" title={t("suppliers.list.forbiddenTitle")}>
          {t("suppliers.list.forbiddenBody")}
        </Alert>
      ) : (
        <div className="space-y-3">
          <StatusFilterTabs activeStatus={activeStatus} />

          {suppliers.length === 0 ? (
            <SuppliersEmptyState filtered={Boolean(activeStatus)} canCreate={permissions.canCreate} />
          ) : (
            <SupplierTable suppliers={suppliers} />
          )}
        </div>
      )}
    </div>
  );
}

async function SuppliersEmptyState({ filtered, canCreate }: { filtered: boolean; canCreate: boolean }) {
  const { t } = await getI18n();
  return (
    <EmptyState
      icon={NAV_ITEMS.suppliers.icon}
      title={filtered ? t("suppliers.list.emptyFilteredTitle") : t("suppliers.list.emptyTitle")}
      description={
        filtered
          ? t("suppliers.list.emptyFilteredBody")
          : t("suppliers.list.emptyBody")
      }
      action={
        filtered ? (
          <Link href="/suppliers" className={buttonClasses("secondary")}>
            {t("suppliers.list.viewAll")}
          </Link>
        ) : canCreate ? (
          <Link href="/suppliers/new" className={buttonClasses("primary")}>
            <Plus className="size-4" aria-hidden="true" />
            {t("suppliers.list.register")}
          </Link>
        ) : undefined
      }
    />
  );
}
