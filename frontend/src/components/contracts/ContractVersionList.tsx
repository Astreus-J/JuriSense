import Link from "next/link";

import { cn } from "@/lib/cn";
import { formatDateTime } from "@/lib/format";
import { ContractVersionStatusBadge } from "./ContractVersionStatusBadge";
import type { ContractVersion } from "@/lib/contracts/types";

interface ContractVersionListProps {
  contractId: string;
  versions: ContractVersion[];
  selectedVersionId: string;
}

/**
 * A Server Component: the selected version is real URL state (`?version=`), not client
 * state (persona: "URL as state" — bookmarkable, shareable, back-button-safe), the same
 * rationale `StatusFilterTabs` documents for Suppliers. Most recent negotiation round
 * first — the API returns them ascending by `version_number`, so this reverses that for
 * display (a reviewer almost always wants the current version, not version 1).
 */
export function ContractVersionList({ contractId, versions, selectedVersionId }: ContractVersionListProps) {
  const descending = [...versions].sort((a, b) => b.versionNumber - a.versionNumber);
  const currentVersionNumber = Math.max(...versions.map((v) => v.versionNumber));

  return (
    <nav aria-label="Contract versions" className="space-y-1.5">
      <h2 className="px-1 text-xs font-semibold uppercase tracking-wide text-foreground-muted">
        Versions
      </h2>
      <ul className="space-y-1.5">
        {descending.map((version) => {
          const isSelected = version.id === selectedVersionId;
          const isCurrent = version.versionNumber === currentVersionNumber;
          return (
            <li key={version.id}>
              <Link
                href={`/contracts/${contractId}?version=${version.versionNumber}`}
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
                    {isCurrent && (
                      <span className="ml-1.5 text-xs font-normal text-foreground-muted">(current)</span>
                    )}
                  </span>
                </div>
                <div className="mt-1.5 flex items-center justify-between gap-2">
                  <ContractVersionStatusBadge status={version.status} />
                  <span className="text-xs text-foreground-muted">{formatDateTime(version.createdAt)}</span>
                </div>
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
