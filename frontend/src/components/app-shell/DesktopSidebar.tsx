import type { NavItem } from "@/lib/navigation/modules";
import type { Membership } from "@/lib/auth/types";
import { Brand } from "./Brand";
import { SidebarContent } from "./SidebarContent";

interface DesktopSidebarProps {
  navItems: NavItem[];
  memberships: Membership[];
  activeOrganizationId: string;
}

export function DesktopSidebar({ navItems, memberships, activeOrganizationId }: DesktopSidebarProps) {
  return (
    <aside className="hidden w-56 shrink-0 flex-col border-r border-border bg-surface-muted md:flex">
      <div className="flex h-14 shrink-0 items-center border-b border-border px-4">
        <Brand />
      </div>
      <div className="flex-1 overflow-y-auto px-3 py-4">
        <SidebarContent
          navItems={navItems}
          memberships={memberships}
          activeOrganizationId={activeOrganizationId}
        />
      </div>
    </aside>
  );
}
