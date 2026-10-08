import Link from "next/link";

import { PolicyVersionStatusBadge } from "./PolicyVersionStatusBadge";
import { cn } from "@/lib/cn";
import { formatDateTime } from "@/lib/format";
import type { PolicyVersion } from "@/lib/policies/types";

interface PolicyVersionListProps {
  policyId: string;
  versions: PolicyVersion[];
  selectedVersionId?: string;
}

/**
 * Most recent first — the API returns versions ascending by `version_number`
 * (`PolicyVersionRepository.list_by_policy`), so this reverses that for display, matching
 * `ContractVersionList`'s identical rationale (a reviewer almost always wants the latest
 * draft or the current published version, not version 1).
 */
export function PolicyVersionList({ policyId, versions, selectedVersionId }: PolicyVersionListProps) {
  const descending = [...versions].sort((a, b) => b.versionNumber - a.versionNumber);

  return (
    <ul className="space-y-1.5">
      {descending.map((version) => {
        const isSelected = version.id === selectedVersionId;
        return (
          <li key={version.id}>
            <Link
              href={`/policies/${policyId}/versions/${version.id}`}
              aria-current={isSelected ? "true" : undefined}
              className={cn(
                "block rounded-lg border px-3 py-2.5 text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring",
                isSelected
                  ? "border-primary bg-surface-muted"
                  : "border-border bg-surface hover:bg-surface-muted",
              )}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-medium text-foreground">
                  Version {version.versionNumber}
                  {version.isCurrent && (
                    <span className="ml-1.5 text-xs font-normal text-foreground-muted">(current)</span>
                  )}
                </span>
              </div>
              <div className="mt-1.5 flex items-center justify-between gap-2">
                <PolicyVersionStatusBadge status={version.status} />
                <span className="text-xs text-foreground-muted">
                  {version.publishedAt
                    ? `Published ${formatDateTime(version.publishedAt)}`
                    : `Created ${formatDateTime(version.createdAt)}`}
                </span>
              </div>
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
