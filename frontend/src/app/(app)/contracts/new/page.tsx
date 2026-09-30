import type { Metadata } from "next";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import { UploadContractForm } from "@/components/contracts/UploadContractForm";
import { readAccessToken } from "@/lib/auth/cookies";
import { requireSession } from "@/lib/auth/session";
import { listContracts } from "@/lib/contracts/backend";
import { listSuppliers } from "@/lib/suppliers/backend";

export const metadata: Metadata = { title: "Upload contract — JuriSense Gate" };

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
  const { contractId } = await searchParams;
  const accessToken = (await readAccessToken())!;

  // Both lists are needed regardless of which flow the user ends up picking (the radio
  // choice is client-side), and both are cheap, org-scoped GETs — fetched together rather
  // than gating one behind the other's result.
  const [suppliers, contracts] = await Promise.all([
    listSuppliers(accessToken),
    listContracts(accessToken),
  ]);

  return (
    <div className="max-w-lg space-y-6">
      <Link
        href="/contracts"
        className="inline-flex items-center gap-1 text-sm font-medium text-foreground-muted hover:text-foreground"
      >
        <ArrowLeft className="size-4" aria-hidden="true" />
        Back to contracts
      </Link>

      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">
          Upload a contract
        </h1>
        <p className="mt-1 text-sm text-foreground-muted">
          JuriSense automatically extracts and structures the contract&apos;s key terms as
          soon as it&apos;s uploaded — parties, value, duration, liability, and more, each
          traceable back to its page and clause.
        </p>
      </div>

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
