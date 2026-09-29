import type { Metadata } from "next";
import Link from "next/link";
import { Plus } from "lucide-react";

import { Alert } from "@/components/ui/Alert";
import { buttonClasses } from "@/components/ui/Button";
import { StatusFilterTabs } from "@/components/suppliers/StatusFilterTabs";
import { SupplierTable } from "@/components/suppliers/SupplierTable";
import { ApiError } from "@/lib/auth/backend";
import { readAccessToken } from "@/lib/auth/cookies";
import { requireSession } from "@/lib/auth/session";
import { NAV_ITEMS } from "@/lib/navigation/modules";
import { listSuppliers } from "@/lib/suppliers/backend";
import { getSupplierPermissions } from "@/lib/suppliers/permissions";
import { SUPPLIER_STATUSES } from "@/lib/suppliers/types";
import type { SupplierStatus } from "@/lib/suppliers/types";

export const metadata: Metadata = { title: "Suppliers — JuriSense Gate" };

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
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">Suppliers</h1>
          <p className="mt-1 max-w-2xl text-sm text-foreground-muted">
            Every supplier your organization has registered, with its verification status
            against official and public sources.
          </p>
        </div>
        {!forbidden && permissions.canCreate && (
          <Link href="/suppliers/new" className={buttonClasses("primary")}>
            <Plus className="size-4" aria-hidden="true" />
            Register supplier
          </Link>
        )}
      </div>

      {forbidden ? (
        <Alert tone="danger" title="You don't have access to Suppliers.">
          Ask an administrator to grant you the &quot;suppliers&quot; read permission for this
          organization.
        </Alert>
      ) : (
        <div className="space-y-4">
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

function SuppliersEmptyState({ filtered, canCreate }: { filtered: boolean; canCreate: boolean }) {
  const Icon = NAV_ITEMS.suppliers.icon;
  return (
    <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-border bg-surface px-6 py-16 text-center">
      <div className="flex size-12 items-center justify-center rounded-full bg-surface-muted">
        <Icon className="size-6 text-foreground-muted" aria-hidden="true" />
      </div>
      <h2 className="text-lg font-semibold text-foreground">
        {filtered ? "No suppliers match this filter" : "No suppliers yet"}
      </h2>
      <p className="max-w-sm text-sm text-foreground-muted">
        {filtered
          ? "Try a different status, or view all suppliers."
          : "Register your first supplier to start tracking its verification status against official and public sources."}
      </p>
      {canCreate && !filtered && (
        <Link href="/suppliers/new" className={buttonClasses("primary", "mt-1")}>
          <Plus className="size-4" aria-hidden="true" />
          Register supplier
        </Link>
      )}
    </div>
  );
}
