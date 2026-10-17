import { StatusBadge } from "@/components/shared/StatusBadge";
import Link from "next/link";

import { cn } from "@/lib/cn";
import { formatDateTime } from "@/lib/format";
import { getI18n } from "@/lib/i18n/server";
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
export async function PolicyVersionList({ policyId, versions, selectedVersionId }: PolicyVersionListProps) {
  const { t, locale } = await getI18n();
  const descending = [...versions].sort((a, b) => b.versionNumber - a.versionNumber);

  return (
    <ul className="divide-y divide-border border-y border-border">
      {descending.map((version) => {
        const isSelected = version.id === selectedVersionId;
        return (
          <li key={version.id}>
            <Link
              href={`/policies/${policyId}/versions/${version.id}`}
              aria-current={isSelected ? "true" : undefined}
              className={cn(
                "flex flex-wrap items-center justify-between gap-x-4 gap-y-1 px-3 py-2.5 transition-colors",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-focus-ring",
                isSelected ? "bg-surface-muted" : "hover:bg-surface-muted",
              )}
            >
              <span className="flex items-center gap-3">
                <span className="text-sm font-medium text-foreground">
                  {t("policies.versionList.version", { number: version.versionNumber })}
                </span>
                <StatusBadge kind="policyVersion" value={version.status} />
                {version.isCurrent && (
                  <span className="text-xs text-foreground-muted">
                    {t("policies.versionList.current")}
                  </span>
                )}
              </span>
              <span className="text-xs tabular-nums text-foreground-muted">
                {version.publishedAt
                  ? t("policies.versionList.published", { date: formatDateTime(version.publishedAt, locale) })
                  : t("policies.versionList.created", { date: formatDateTime(version.createdAt, locale) })}
              </span>
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
