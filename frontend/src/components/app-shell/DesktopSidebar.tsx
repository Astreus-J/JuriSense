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
    <aside className="hidden w-64 shrink-0 flex-col border-r border-border bg-surface px-4 py-5 md:flex">
      <div className="mb-6 px-1">
        <Brand />
      </div>
      <SidebarContent
        navItems={navItems}
        memberships={memberships}
        activeOrganizationId={activeOrganizationId}
      />
    </aside>
  );
}
