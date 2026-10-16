import type { Metadata } from "next";
import Link from "next/link";
import { Plus } from "lucide-react";

import { Alert } from "@/components/ui/Alert";
import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { buttonClasses } from "@/components/ui/Button";
import { ContractTable } from "@/components/contracts/ContractTable";
import { ApiError } from "@/lib/auth/backend";
import { readAccessToken } from "@/lib/auth/cookies";
import { requireSession } from "@/lib/auth/session";
import { listContracts } from "@/lib/contracts/backend";
import { getContractPermissions } from "@/lib/contracts/permissions";
import { NAV_ITEMS } from "@/lib/navigation/modules";
import { listSuppliers } from "@/lib/suppliers/backend";

export const metadata: Metadata = { title: "Contracts — JuriSense Gate" };

/**
 * No status filter here (unlike Suppliers' `StatusFilterTabs`): the brief leaves this to
 * judgment, and with `ContractStatus` mostly reflecting the commercial lifecycle rather
 * than something a reviewer triages by day-to-day, a single most-recently-updated-first
 * list is enough for this epic's scope — add filtering if/when the list actually grows
 * unwieldy in practice, not preemptively.
 */
export default async function ContractsPage() {
  const user = await requireSession();
  const permissions = getContractPermissions(user.role);
  const accessToken = (await readAccessToken())!;

  let contracts: Awaited<ReturnType<typeof listContracts>> = [];
  let forbidden = false;

  try {
    contracts = await listContracts(accessToken);
  } catch (error) {
    if (error instanceof ApiError && error.status === 403) {
      forbidden = true;
    } else {
      throw error;
    }
  }

  // Best-effort supplier-name lookup for the table's "Supplier" column — every role with
  // Contracts read access also has at least Suppliers read access in the default RBAC
  // grid (`backend/app/identity/domain/rbac.py`), but a per-user override could still
  // narrow that, so a failure here degrades to showing raw ids rather than breaking the
  // whole page (persona: "design the unhappy paths").
  const supplierNames = new Map<string, string>();
  if (!forbidden && contracts.length > 0) {
    try {
      const suppliers = await listSuppliers(accessToken);
      for (const supplier of suppliers) supplierNames.set(supplier.id, supplier.legalName);
    } catch {
      // Leave supplierNames empty — ContractTable already falls back to "—" per row.
    }
  }

  return (
    <div className="space-y-5">
      <PageHeader
        title="Contracts"
        description="Every contract your organization has uploaded, with the structured, cited extraction behind each version."
        actions={
          !forbidden && permissions.canCreate ? (
            <Link href="/contracts/new" className={buttonClasses("primary")}>
              <Plus className="size-4" aria-hidden="true" />
              Upload contract
            </Link>
          ) : undefined
        }
      />

      {forbidden ? (
        <Alert tone="danger" title="You don't have access to Contracts.">
          Ask an administrator to grant you the &quot;contracts&quot; read permission for
          this organization.
        </Alert>
      ) : contracts.length === 0 ? (
        <ContractsEmptyState canCreate={permissions.canCreate} />
      ) : (
        <ContractTable contracts={contracts} supplierNames={supplierNames} />
      )}
    </div>
  );
}

function ContractsEmptyState({ canCreate }: { canCreate: boolean }) {
  return (
    <EmptyState
      icon={NAV_ITEMS.contracts.icon}
      title="No contracts yet"
      description={
        canCreate
          ? "Upload your first contract to start tracking its structured, cited extraction against your policies."
          : "No contracts have been uploaded for your organization yet."
      }
      action={
        canCreate ? (
          <Link href="/contracts/new" className={buttonClasses("primary")}>
            <Plus className="size-4" aria-hidden="true" />
            Upload contract
          </Link>
        ) : undefined
      }
    />
  );
}
