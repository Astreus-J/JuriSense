import Link from "next/link";

import { ContractStatusBadge } from "./ContractStatusBadge";
import { formatDateTime } from "@/lib/format";
import type { Contract } from "@/lib/contracts/types";

interface ContractTableProps {
  contracts: Contract[];
  /** supplierId -> legal name, best-effort (see the caller's note on why this can be
   * incomplete for a subset of rows without failing the whole page). */
  supplierNames: Map<string, string>;
}

export function ContractTable({ contracts, supplierNames }: ContractTableProps) {
  return (
    <div className="overflow-x-auto rounded-xl border border-border bg-surface">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-border bg-surface-muted text-xs uppercase tracking-wide text-foreground-muted">
          <tr>
            <th className="px-4 py-3 font-medium">Title</th>
            <th className="px-4 py-3 font-medium">Supplier</th>
            <th className="px-4 py-3 font-medium">Type</th>
            <th className="px-4 py-3 font-medium">Status</th>
            <th className="px-4 py-3 font-medium">Updated</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {contracts.map((contract) => (
            <tr key={contract.id} className="hover:bg-surface-muted">
              <td className="px-4 py-3 font-medium text-foreground">
                <Link
                  href={`/contracts/${contract.id}`}
                  className="rounded hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring"
                >
                  {contract.title}
                </Link>
              </td>
              <td className="px-4 py-3 text-foreground-muted">
                {supplierNames.get(contract.supplierId) ?? "—"}
              </td>
              <td className="px-4 py-3 text-foreground-muted">{contract.contractType}</td>
              <td className="px-4 py-3">
                <ContractStatusBadge status={contract.status} />
              </td>
              <td className="px-4 py-3 whitespace-nowrap text-foreground-muted">
                {formatDateTime(contract.updatedAt)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
