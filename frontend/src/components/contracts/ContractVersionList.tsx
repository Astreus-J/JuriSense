import { StatusBadge } from "@/components/shared/StatusBadge";
import Link from "next/link";

import { cn } from "@/lib/cn";
import { formatDateTime } from "@/lib/format";
import { getI18n } from "@/lib/i18n/server";
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
 *
 * Rendered as a flat vertical rail (a timeline-like list with a selection marker) rather
 * than a stack of cards: it is navigation, not content.
 */
export async function ContractVersionList({ contractId, versions, selectedVersionId }: ContractVersionListProps) {
  const { t, locale } = await getI18n();
  const descending = [...versions].sort((a, b) => b.versionNumber - a.versionNumber);
  const currentVersionNumber = Math.max(...versions.map((v) => v.versionNumber));

  return (
    <nav aria-label={t("contracts.versions.nav")} className="min-w-0">
      <h2 className="pb-2 text-[12px] font-medium uppercase tracking-wider text-foreground-muted">
        {t("contracts.versions.heading")}
      </h2>
      <ul className="flex gap-2 overflow-x-auto pb-1 lg:flex-col lg:gap-0 lg:overflow-visible lg:border-l lg:border-border lg:pb-0">
        {descending.map((version) => {
          const isSelected = version.id === selectedVersionId;
          const isCurrent = version.versionNumber === currentVersionNumber;
          return (
            <li key={version.id} className="shrink-0">
              <Link
                href={`/contracts/${contractId}?version=${version.versionNumber}`}
                aria-current={isSelected ? "true" : undefined}
                className={cn(
                  "block rounded-md px-3 py-2 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring",
                  "lg:-ml-px lg:rounded-none lg:rounded-r-md lg:border-l-2",
                  isSelected
                    ? "bg-surface-muted lg:border-primary"
                    : "hover:bg-surface-muted lg:border-transparent",
                )}
              >
                <span className="flex items-baseline gap-1.5 text-[14px] font-medium text-foreground">
                  {t("contracts.versions.version", { number: version.versionNumber })}
                  {isCurrent && (
                    <span className="text-xs font-normal text-foreground-muted">
                      {t("contracts.versions.current")}
                    </span>
                  )}
                </span>
                <span className="mt-1 block">
                  <StatusBadge kind="contractVersion" value={version.status} />
                </span>
                <span className="mt-1 block text-xs tabular-nums text-foreground-muted">
                  {formatDateTime(version.createdAt, locale)}
                </span>
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
