import { StatusBadge } from "@/components/shared/StatusBadge";
import { DataTable, RowLink, Td, Th, Tr } from "@/components/ui/DataTable";
import { formatDateTime } from "@/lib/format";
import { getI18n } from "@/lib/i18n/server";
import type { Contract } from "@/lib/contracts/types";

interface ContractTableProps {
  contracts: Contract[];
  /** supplierId -> legal name, best-effort (see the caller's note on why this can be
   * incomplete for a subset of rows without failing the whole page). */
  supplierNames: Map<string, string>;
}

export async function ContractTable({ contracts, supplierNames }: ContractTableProps) {
  const { t, locale } = await getI18n();
  return (
    <DataTable caption={t("contracts.table.caption")}>
      <thead>
        <tr>
          <Th>{t("contracts.table.title")}</Th>
          <Th>{t("contracts.table.supplier")}</Th>
          <Th>{t("contracts.table.type")}</Th>
          <Th>{t("contracts.table.status")}</Th>
          <Th numeric>{t("contracts.table.updated")}</Th>
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
              {formatDateTime(contract.updatedAt, locale)}
            </Td>
          </Tr>
        ))}
      </tbody>
    </DataTable>
  );
}
