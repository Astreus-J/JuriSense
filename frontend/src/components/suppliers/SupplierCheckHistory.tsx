import { StatusBadge } from "@/components/shared/StatusBadge";
import { DataTable, Td, Th, Tr } from "@/components/ui/DataTable";
import { EmptyState } from "@/components/ui/EmptyState";
import { formatDateTime } from "@/lib/format";
import type { SupplierCheck } from "@/lib/suppliers/types";

interface SupplierCheckHistoryProps {
  checks: SupplierCheck[];
}

/** SUP-005: the full, immutable SupplierCheck history, most recent first (the API's own order). */
export function SupplierCheckHistory({ checks }: SupplierCheckHistoryProps) {
  return (
    <section className="space-y-3">
      <h2 className="text-base font-semibold text-foreground">Verification history</h2>

      {checks.length === 0 ? (
        <EmptyState
          title="No verification checks yet"
          description="Each check against official and public sources is recorded here and cannot be edited afterwards."
        />
      ) : (
        <DataTable caption="Supplier verification checks, most recent first">
          <thead>
            <tr>
              <Th>Status</Th>
              <Th>Sources consulted</Th>
              <Th>Started</Th>
              <Th>Completed</Th>
              <Th>Failure reason</Th>
            </tr>
          </thead>
          <tbody>
            {checks.map((check) => (
              <Tr key={check.id}>
                <Td>
                  <StatusBadge kind="supplierCheck" value={check.status} />
                </Td>
                <Td muted>
                  {check.sourcesConsulted.length > 0 ? check.sourcesConsulted.join(", ") : "—"}
                </Td>
                <Td muted className="whitespace-nowrap tabular-nums">
                  {formatDateTime(check.startedAt)}
                </Td>
                <Td muted className="whitespace-nowrap tabular-nums">
                  {check.completedAt ? formatDateTime(check.completedAt) : "—"}
                </Td>
                <Td muted>
                  {check.status === "failed" && check.failureReason ? check.failureReason : "—"}
                </Td>
              </Tr>
            ))}
          </tbody>
        </DataTable>
      )}
    </section>
  );
}
