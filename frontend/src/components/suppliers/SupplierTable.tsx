import { StatusBadge } from "@/components/shared/StatusBadge";
import { DataTable, RowLink, Td, Th, Tr } from "@/components/ui/DataTable";
import { getI18n } from "@/lib/i18n/server";
import type { Supplier } from "@/lib/suppliers/types";

interface SupplierTableProps {
  suppliers: Supplier[];
}

export async function SupplierTable({ suppliers }: SupplierTableProps) {
  const { t } = await getI18n();
  return (
    <DataTable caption={t("suppliers.table.caption")}>
      <thead>
        <tr>
          <Th>{t("suppliers.table.legalName")}</Th>
          <Th>{t("suppliers.table.taxId")}</Th>
          <Th>{t("suppliers.table.jurisdiction")}</Th>
          <Th>{t("suppliers.table.status")}</Th>
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
