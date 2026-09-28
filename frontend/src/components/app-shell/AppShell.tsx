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
 */
export function AppShell({ user, children }: AppShellProps) {
  const navItems = getNavItemsForRole(user.role);

  return (
    <div className="flex h-screen overflow-hidden bg-surface-muted">
      <DesktopSidebar
        navItems={navItems}
        memberships={user.memberships}
        activeOrganizationId={user.organizationId}
      />
      <div className="flex flex-1 flex-col overflow-hidden">
        <TopBar
          navItems={navItems}
          memberships={user.memberships}
          activeOrganizationId={user.organizationId}
          fullName={user.fullName}
          email={user.email}
          role={user.role}
        />
        <main className="flex-1 overflow-y-auto p-4 md:p-8">
          <div className="mx-auto max-w-5xl">{children}</div>
        </main>
      </div>
    </div>
  );
}
