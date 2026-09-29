import { formatDateTime } from "@/lib/format";
import type { SupplierCheck } from "@/lib/suppliers/types";
import { SupplierCheckStatusBadge } from "./SupplierCheckStatusBadge";

interface SupplierCheckHistoryProps {
  checks: SupplierCheck[];
}

/** SUP-005: the full, immutable SupplierCheck history, most recent first (the API's own order). */
export function SupplierCheckHistory({ checks }: SupplierCheckHistoryProps) {
  return (
    <section className="space-y-3">
      <h2 className="text-sm font-semibold text-foreground">Verification history</h2>

      {checks.length === 0 ? (
        <p className="rounded-xl border border-dashed border-border bg-surface px-6 py-10 text-center text-sm text-foreground-muted">
          No verification checks have run yet.
        </p>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-border bg-surface">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-border bg-surface-muted text-xs uppercase tracking-wide text-foreground-muted">
              <tr>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Sources consulted</th>
                <th className="px-4 py-3 font-medium">Started</th>
                <th className="px-4 py-3 font-medium">Completed</th>
                <th className="px-4 py-3 font-medium">Failure reason</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {checks.map((check) => (
                <tr key={check.id}>
                  <td className="px-4 py-3">
                    <SupplierCheckStatusBadge status={check.status} />
                  </td>
                  <td className="px-4 py-3 text-foreground-muted">
                    {check.sourcesConsulted.length > 0 ? check.sourcesConsulted.join(", ") : "—"}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-foreground-muted">
                    {formatDateTime(check.startedAt)}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-foreground-muted">
                    {check.completedAt ? formatDateTime(check.completedAt) : "—"}
                  </td>
                  <td className="px-4 py-3 text-foreground-muted">
                    {check.status === "failed" && check.failureReason ? check.failureReason : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
