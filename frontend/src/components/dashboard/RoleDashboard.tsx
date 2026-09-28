import Link from "next/link";
import { ArrowRight } from "lucide-react";

import { formatRoleLabel } from "@/lib/auth/types";
import type { Role } from "@/lib/auth/types";
import { NAV_ITEMS } from "@/lib/navigation/modules";
import { ROLE_DASHBOARD_COPY } from "@/lib/navigation/dashboard-copy";

interface RoleDashboardProps {
  fullName: string;
  role: Role;
}

/**
 * The dashboard home (STORY-1.2.1). Nothing in the product exists yet for
 * any organization on day one, so this doubles as the empty state for every
 * one of the 10 roles: what's empty, why, and what to do next, tailored per
 * role (`src/lib/navigation/dashboard-copy.ts`) instead of one generic
 * "Welcome!" screen.
 */
export function RoleDashboard({ fullName, role }: RoleDashboardProps) {
  const copy = ROLE_DASHBOARD_COPY[role];
  const firstName = fullName.trim().split(/\s+/)[0] ?? fullName;

  return (
    <div className="space-y-8">
      <div>
        <p className="text-sm font-medium text-foreground-muted">
          Welcome, {firstName} · {formatRoleLabel(role)}
        </p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight text-foreground">
          {copy.headline}
        </h1>
        <p className="mt-2 max-w-2xl text-sm text-foreground-muted">{copy.subtext}</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {copy.highlights.map((highlight) => {
          const Icon = highlight.icon;
          const href = NAV_ITEMS[highlight.moduleKey].href;
          return (
            <Link
              key={highlight.title}
              href={href}
              className="group flex flex-col gap-3 rounded-xl border border-border bg-surface p-5 transition-colors hover:border-border-strong hover:bg-surface-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring"
            >
              <div className="flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <Icon className="size-5" aria-hidden="true" />
              </div>
              <div>
                <h2 className="text-sm font-semibold text-foreground">{highlight.title}</h2>
                <p className="mt-1 text-sm text-foreground-muted">{highlight.description}</p>
              </div>
              <span className="mt-auto flex items-center gap-1 text-sm font-medium text-primary opacity-0 transition-opacity group-hover:opacity-100">
                Go there
                <ArrowRight className="size-3.5" aria-hidden="true" />
              </span>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
