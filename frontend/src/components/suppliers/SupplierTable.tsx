import { StatusBadge } from "@/components/shared/StatusBadge";
import { DataTable, RowLink, Td, Th, Tr } from "@/components/ui/DataTable";
import type { Supplier } from "@/lib/suppliers/types";

interface SupplierTableProps {
  suppliers: Supplier[];
}

export function SupplierTable({ suppliers }: SupplierTableProps) {
  return (
    <DataTable caption="Registered suppliers">
      <thead>
        <tr>
          <Th>Legal name</Th>
          <Th>Tax ID</Th>
          <Th>Jurisdiction</Th>
          <Th>Status</Th>
        </tr>
      </thead>
      <tbody>
        {suppliers.map((supplier) => (
          <Tr key={supplier.id}>
            <Td className="w-full">
              <RowLink href={`/suppliers/${supplier.id}`}>{supplier.legalName}</RowLink>
            </Td>
            <Td muted className="whitespace-nowrap font-mono text-xs tabular-nums">
              {supplier.taxId}
            </Td>
            <Td muted className="whitespace-nowrap">
              {supplier.jurisdiction}
            </Td>
            <Td>
              <StatusBadge kind="supplier" value={supplier.status} />
            </Td>
          </Tr>
        ))}
      </tbody>
    </DataTable>
  );
}
