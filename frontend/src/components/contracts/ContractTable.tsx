import { StatusBadge } from "@/components/shared/StatusBadge";
import { DataTable, RowLink, Td, Th, Tr } from "@/components/ui/DataTable";
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
    <DataTable caption="Uploaded contracts, most recently updated first">
      <thead>
        <tr>
          <Th>Title</Th>
          <Th>Supplier</Th>
          <Th>Type</Th>
          <Th>Status</Th>
          <Th numeric>Updated</Th>
        </tr>
      </thead>
      <tbody>
        {contracts.map((contract) => (
          <Tr key={contract.id}>
            <Td className="w-full">
              <RowLink href={`/contracts/${contract.id}`}>{contract.title}</RowLink>
            </Td>
            <Td muted className="whitespace-nowrap">
              {supplierNames.get(contract.supplierId) ?? "—"}
            </Td>
            <Td muted className="whitespace-nowrap">
              {contract.contractType}
            </Td>
            <Td>
              <StatusBadge kind="contract" value={contract.status} />
            </Td>
            <Td numeric muted className="whitespace-nowrap">
              {formatDateTime(contract.updatedAt)}
            </Td>
          </Tr>
        ))}
      </tbody>
    </DataTable>
  );
}
