import Link from "next/link";
import { ArrowRight } from "lucide-react";

import { PageHeader } from "@/components/ui/PageHeader";
import type { Role } from "@/lib/auth/types";
import { getI18n } from "@/lib/i18n/server";
import { NAV_ITEMS } from "@/lib/navigation/modules";
import { ROLE_DASHBOARD_HIGHLIGHTS } from "@/lib/navigation/dashboard-copy";

interface RoleDashboardProps {
  fullName: string;
  role: Role;
}

/**
 * The dashboard home (STORY-1.2.1). Nothing in the product exists yet for
 * any organization on day one, so this doubles as the empty state for every
 * one of the 10 roles: what's empty, why, and what to do next, tailored per
 * role (`dashboard.roles.*` / `dashboard.highlights.*` in the message catalogs) instead of one generic
 * "Welcome!" screen.
 */
export async function RoleDashboard({ fullName, role }: RoleDashboardProps) {
  const { t } = await getI18n();
  const highlights = ROLE_DASHBOARD_HIGHLIGHTS[role];
  const firstName = fullName.trim().split(/\s+/)[0] ?? fullName;

  return (
    <div className="space-y-6">
      <PageHeader
        title={t(`dashboard.roles.${role}.headline`)}
        description={t(`dashboard.roles.${role}.subtext`)}
        meta={
          <span className="text-sm text-foreground-muted">
            {t("dashboard.signedInAs")} <span className="font-medium text-foreground">{firstName}</span> ·{" "}
            {t(`role.${role}`)}
          </span>
        }
      />

      <section aria-labelledby="dashboard-start" className="space-y-2">
        <h2 id="dashboard-start" className="text-base font-semibold text-foreground">
          {t("dashboard.whereToStart")}
        </h2>
        <ul className="grid border-t border-border lg:grid-cols-2 lg:gap-x-8">
          {highlights.map((highlight) => {
            const Icon = highlight.icon;
            const href = NAV_ITEMS[highlight.moduleKey].href;
            return (
              <li key={highlight.id} className="border-b border-border">
                <Link
                  href={href}
                  className="group flex items-start gap-3 rounded-md px-1 py-3 transition-colors hover:bg-surface-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-focus-ring"
                >
                  <Icon className="mt-0.5 size-4 shrink-0 text-foreground-muted" aria-hidden="true" />
                  <span className="min-w-0 flex-1">
                    <span className="block text-sm font-medium text-foreground">{t(`dashboard.highlights.${highlight.id}.title`)}</span>
                    <span className="mt-0.5 block text-sm text-foreground-muted">
                      {t(`dashboard.highlights.${highlight.id}.description`)}
                    </span>
                  </span>
                  <ArrowRight
                    className="mt-0.5 size-4 shrink-0 text-foreground-muted transition-transform group-hover:translate-x-0.5 group-hover:text-primary motion-reduce:transition-none"
                    aria-hidden="true"
                  />
                </Link>
              </li>
            );
          })}
        </ul>
      </section>
    </div>
  );
}
