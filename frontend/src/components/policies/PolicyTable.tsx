import { StatusBadge } from "@/components/shared/StatusBadge";
import { DataTable, RowLink, Td, Th, Tr } from "@/components/ui/DataTable";
import { formatDateTime } from "@/lib/format";
import { getI18n } from "@/lib/i18n/server";
import type { Policy } from "@/lib/policies/types";

interface PolicyTableProps {
  policies: Policy[];
}

export async function PolicyTable({ policies }: PolicyTableProps) {
  const { t, locale } = await getI18n();
  return (
    <DataTable caption={t("policies.table.caption")}>
      <thead>
        <tr>
          <Th>{t("policies.table.name")}</Th>
          <Th>{t("policies.table.status")}</Th>
          <Th numeric>{t("policies.table.updated")}</Th>
        </tr>
      </thead>
      <tbody>
        {policies.map((policy) => (
          <Tr key={policy.id}>
            <Td className="w-full">
              <RowLink href={`/policies/${policy.id}`}>{policy.name}</RowLink>
            </Td>
            <Td>
              <StatusBadge kind="policy" value={policy.status} />
            </Td>
            <Td numeric muted className="whitespace-nowrap">
              {formatDateTime(policy.updatedAt, locale)}
            </Td>
          </Tr>
        ))}
      </tbody>
    </DataTable>
  );
}
