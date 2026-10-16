"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

interface NavLinkProps {
  href: string;
  label: string;
  /** Pre-rendered by the server (see `SidebarContent`) — a component
   * reference cannot cross the Server→Client boundary, only an already
   *-rendered element can. */
  icon: ReactNode;
}

export function NavLink({ href, label, icon }: NavLinkProps) {
  const pathname = usePathname();
  // `/settings/organization` should keep Settings highlighted for sibling settings routes.
  const section = href.startsWith("/settings") ? "/settings" : href;
  const isActive = pathname === section || pathname.startsWith(`${section}/`);

  return (
    <Link
      href={href}
      aria-current={isActive ? "page" : undefined}
      className={cn(
        "flex items-center gap-2.5 rounded-md px-2.5 py-1.5 text-[14px] font-medium transition-colors",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring",
        isActive
          ? "bg-surface text-foreground shadow-[inset_2px_0_0_var(--primary)] ring-1 ring-border"
          : "text-foreground-muted hover:bg-surface hover:text-foreground",
      )}
    >
      <span className={isActive ? "text-primary" : undefined}>{icon}</span>
      {label}
    </Link>
  );
}
