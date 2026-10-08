import Link from "next/link";

import { PolicyStatusBadge } from "./PolicyStatusBadge";
import { formatDateTime } from "@/lib/format";
import type { Policy } from "@/lib/policies/types";

interface PolicyTableProps {
  policies: Policy[];
}

export function PolicyTable({ policies }: PolicyTableProps) {
  return (
    <div className="overflow-x-auto rounded-xl border border-border bg-surface">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-border bg-surface-muted text-xs uppercase tracking-wide text-foreground-muted">
          <tr>
            <th className="px-4 py-3 font-medium">Name</th>
            <th className="px-4 py-3 font-medium">Status</th>
            <th className="px-4 py-3 font-medium">Last updated</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {policies.map((policy) => (
            <tr key={policy.id} className="hover:bg-surface-muted">
              <td className="px-4 py-3 font-medium text-foreground">
                <Link
                  href={`/policies/${policy.id}`}
                  className="rounded hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring"
                >
                  {policy.name}
                </Link>
              </td>
              <td className="px-4 py-3">
                <PolicyStatusBadge status={policy.status} />
              </td>
              <td className="px-4 py-3 text-foreground-muted">{formatDateTime(policy.updatedAt)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
