import { LocaleSwitcher } from "@/components/i18n/LocaleSwitcher";
import type { NavItem } from "@/lib/navigation/modules";
import type { Membership, Role } from "@/lib/auth/types";
import { MobileNav } from "./MobileNav";
import { SidebarContent } from "./SidebarContent";
import { UserMenu } from "./UserMenu";

interface TopBarProps {
  navItems: NavItem[];
  memberships: Membership[];
  activeOrganizationId: string;
  fullName: string;
  email: string;
  role: Role;
}

export function TopBar({
  navItems,
  memberships,
  activeOrganizationId,
  fullName,
  email,
  role,
}: TopBarProps) {
  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-border bg-canvas px-3 md:px-6">
      <MobileNav>
        <SidebarContent
          navItems={navItems}
          memberships={memberships}
          activeOrganizationId={activeOrganizationId}
        />
      </MobileNav>
      <div className="flex-1" />
      <div className="flex items-center gap-3">
        <LocaleSwitcher />
        <UserMenu fullName={fullName} email={email} role={role} />
      </div>
    </header>
  );
}
