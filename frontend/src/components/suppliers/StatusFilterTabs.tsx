import Link from "next/link";

import { cn } from "@/lib/cn";
import { getI18n } from "@/lib/i18n/server";
import { SUPPLIER_STATUSES } from "@/lib/suppliers/types";
import type { SupplierStatus } from "@/lib/suppliers/types";

interface StatusFilterTabsProps {
  activeStatus?: SupplierStatus;
}

/**
 * A Server Component: filtering is real URL state (`?status=`), not client state, so a
 * plain `<Link>` is enough — no `usePathname`/"use client" needed (unlike the sidebar's
 * `NavLink`, which must react to client-side navigation to highlight the *current app
 * section* across many routes). This makes the filter bookmarkable/shareable/back-button
 * -safe for free (persona: "URL as state").
 */
export async function StatusFilterTabs({ activeStatus }: StatusFilterTabsProps) {
  const { t } = await getI18n();
  const tabs: Array<{ key: SupplierStatus | "all"; label: string; href: string }> = [
    { key: "all", label: t("suppliers.list.filterAll"), href: "/suppliers" },
    ...SUPPLIER_STATUSES.map((status) => ({
      key: status,
      label: t(`status.supplier.${status}`),
      href: `/suppliers?status=${status}`,
    })),
  ];

  return (
    <nav aria-label={t("suppliers.list.filterNav")} className="flex flex-wrap gap-x-1 border-b border-border">
      {tabs.map((tab) => {
        const isActive = tab.key === "all" ? !activeStatus : tab.key === activeStatus;
        return (
          <Link
            key={tab.key}
            href={tab.href}
            aria-current={isActive ? "page" : undefined}
            className={cn(
              "-mb-px border-b-2 px-2.5 py-2 text-[14px] font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring",
              isActive
                ? "border-primary text-primary"
                : "border-transparent text-foreground-muted hover:text-foreground",
            )}
          >
            {tab.label}
          </Link>
        );
      })}
    </nav>
  );
}
