import { StatusBadge } from "@/components/shared/StatusBadge";
import { DataTable, RowLink, Td, Th, Tr } from "@/components/ui/DataTable";
import { formatDateTime } from "@/lib/format";
import type { Policy } from "@/lib/policies/types";

interface PolicyTableProps {
  policies: Policy[];
}

export function PolicyTable({ policies }: PolicyTableProps) {
  return (
    <DataTable caption="Policies">
      <thead>
        <tr>
          <Th>Name</Th>
          <Th>Status</Th>
          <Th numeric>Last updated</Th>
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
              {formatDateTime(policy.updatedAt)}
            </Td>
          </Tr>
        ))}
      </tbody>
    </DataTable>
  );
}
