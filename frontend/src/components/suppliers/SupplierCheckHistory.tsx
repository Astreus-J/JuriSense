import { StatusBadge } from "@/components/shared/StatusBadge";
import { DataTable, Td, Th, Tr } from "@/components/ui/DataTable";
import { EmptyState } from "@/components/ui/EmptyState";
import { formatDateTime } from "@/lib/format";
import { getI18n } from "@/lib/i18n/server";
import type { SupplierCheck } from "@/lib/suppliers/types";

interface SupplierCheckHistoryProps {
  checks: SupplierCheck[];
}

/** SUP-005: the full, immutable SupplierCheck history, most recent first (the API's own order). */
export async function SupplierCheckHistory({ checks }: SupplierCheckHistoryProps) {
  const { t, locale } = await getI18n();
  return (
    <section className="space-y-3">
      <h2 className="text-base font-semibold text-foreground">{t("suppliers.history.title")}</h2>

      {checks.length === 0 ? (
        <EmptyState
          title={t("suppliers.history.emptyTitle")}
          description={t("suppliers.history.emptyBody")}
        />
      ) : (
        <DataTable caption={t("suppliers.history.caption")}>
          <thead>
            <tr>
              <Th>{t("suppliers.history.status")}</Th>
              <Th>{t("suppliers.history.sources")}</Th>
              <Th>{t("suppliers.history.started")}</Th>
              <Th>{t("suppliers.history.completed")}</Th>
              <Th>{t("suppliers.history.failureReason")}</Th>
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
                  {formatDateTime(check.startedAt, locale)}
                </Td>
                <Td muted className="whitespace-nowrap tabular-nums">
                  {check.completedAt ? formatDateTime(check.completedAt, locale) : "—"}
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
