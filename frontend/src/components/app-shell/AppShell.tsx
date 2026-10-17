import type { ReactNode } from "react";

import { getNavItemsForRole } from "@/lib/navigation/modules";
import type { SessionUser } from "@/lib/auth/types";
import { DesktopSidebar } from "./DesktopSidebar";
import { TopBar } from "./TopBar";

interface AppShellProps {
  user: SessionUser;
  children: ReactNode;
}

/**
 * The authenticated app shell every future screen mounts into
 * (STORY-1.2.1). Nav items are derived purely from `user.role` via
 * `getNavItemsForRole` — see `src/lib/navigation/modules.ts` for the
 * role→nav mapping and its rationale, and
 * `src/app/(app)/layout.tsx` for where `user` comes from.
 *
 * Accessibility: a skip link is the first focusable element, and `<main id="main"
 * tabIndex={-1}>` is its target (programmatic focus only, so it never shows a focus ring).
 */
export function AppShell({ user, children }: AppShellProps) {
  const navItems = getNavItemsForRole(user.role);

  return (
    <div className="flex h-screen overflow-hidden bg-surface text-sm text-foreground">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-50 focus:rounded-md focus:bg-primary focus:px-3 focus:py-2 focus:text-sm focus:font-medium focus:text-primary-foreground focus:outline-none focus:ring-2 focus:ring-focus-ring focus:ring-offset-2"
      >
        Skip to content
      </a>
      <DesktopSidebar
        navItems={navItems}
        memberships={user.memberships}
        activeOrganizationId={user.organizationId}
      />
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <TopBar
          navItems={navItems}
          memberships={user.memberships}
          activeOrganizationId={user.organizationId}
          fullName={user.fullName}
          email={user.email}
          role={user.role}
        />
        <main id="main" tabIndex={-1} className="flex-1 overflow-y-auto bg-canvas focus:outline-none">
          <div className="mx-auto w-full max-w-6xl px-4 py-6 md:px-8 md:py-8">{children}</div>
        </main>
      </div>
    </div>
  );
}
