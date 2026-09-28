import type { NavItem } from "@/lib/navigation/modules";
import type { Membership } from "@/lib/auth/types";
import { NavLink } from "./NavLink";
import { OrgSwitcher } from "./OrgSwitcher";

interface SidebarContentProps {
  navItems: NavItem[];
  memberships: Membership[];
  activeOrganizationId: string;
}

/** The nav content shared by the persistent desktop sidebar and the mobile drawer. */
export function SidebarContent({ navItems, memberships, activeOrganizationId }: SidebarContentProps) {
  return (
    <div className="flex h-full flex-col gap-4">
      <OrgSwitcher memberships={memberships} activeOrganizationId={activeOrganizationId} />
      <nav aria-label="Primary" className="flex flex-1 flex-col gap-1">
        {navItems.map((item) => (
          <NavLink
            key={item.key}
            href={item.href}
            label={item.label}
            // Render the icon here, server-side, into a plain ReactNode
            // (Next.js Server→Client Components can only cross the boundary
            // as serializable elements, never as raw component/function
            // references — see `node_modules/next/dist/docs/01-app/
            // 01-getting-started/05-server-and-client-components.md`,
            // "Passing props from Server to Client Components (Serialization)").
            icon={<item.icon className="size-4 shrink-0" aria-hidden="true" />}
          />
        ))}
      </nav>
    </div>
  );
}
