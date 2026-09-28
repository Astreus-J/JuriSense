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
  const isActive = pathname === href || pathname.startsWith(`${href}/`);

  return (
    <Link
      href={href}
      aria-current={isActive ? "page" : undefined}
      className={cn(
        "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring",
        isActive
          ? "bg-primary/10 text-primary"
          : "text-foreground-muted hover:bg-surface-muted hover:text-foreground",
      )}
    >
      {icon}
      {label}
    </Link>
  );
}
