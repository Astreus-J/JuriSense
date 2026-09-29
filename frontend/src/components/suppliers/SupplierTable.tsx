import Link from "next/link";

import { SupplierStatusBadge } from "./SupplierStatusBadge";
import type { Supplier } from "@/lib/suppliers/types";

interface SupplierTableProps {
  suppliers: Supplier[];
}

export function SupplierTable({ suppliers }: SupplierTableProps) {
  return (
    <div className="overflow-x-auto rounded-xl border border-border bg-surface">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-border bg-surface-muted text-xs uppercase tracking-wide text-foreground-muted">
          <tr>
            <th className="px-4 py-3 font-medium">Legal name</th>
            <th className="px-4 py-3 font-medium">Tax ID</th>
            <th className="px-4 py-3 font-medium">Jurisdiction</th>
            <th className="px-4 py-3 font-medium">Status</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {suppliers.map((supplier) => (
            <tr key={supplier.id} className="hover:bg-surface-muted">
              <td className="px-4 py-3 font-medium text-foreground">
                <Link
                  href={`/suppliers/${supplier.id}`}
                  className="rounded hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring"
                >
                  {supplier.legalName}
                </Link>
              </td>
              <td className="px-4 py-3 text-foreground-muted">{supplier.taxId}</td>
              <td className="px-4 py-3 text-foreground-muted">{supplier.jurisdiction}</td>
              <td className="px-4 py-3">
                <SupplierStatusBadge status={supplier.status} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
