"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ChevronDown, LogOut, User } from "lucide-react";

import { cn } from "@/lib/cn";
import { formatRoleLabel } from "@/lib/auth/types";
import type { Role } from "@/lib/auth/types";
import { useDropdownMenu } from "./useDropdownMenu";

interface UserMenuProps {
  fullName: string;
  email: string;
  role: Role;
}

export function UserMenu({ fullName, email, role }: UserMenuProps) {
  const router = useRouter();
  const { open, setOpen, containerRef, triggerRef, registerItem, handleItemKeyDown } =
    useDropdownMenu();
  const [signingOut, setSigningOut] = useState(false);

  async function handleSignOut() {
    setSigningOut(true);
    try {
      await fetch("/api/session/logout", { method: "POST" });
    } catch (error) {
      // #135: best-effort, same as the Route Handler's own "always clear the local
      // session no matter what" contract (`src/app/api/session/logout/route.ts`) -- a
      // network failure here must not surface as an unhandled promise rejection; the
      // user still gets signed out locally via the redirect below.
      console.error("Logout request failed", error);
    } finally {
      router.push("/login");
      router.refresh();
    }
  }

  return (
    <div ref={containerRef} className="relative">
      <button
        ref={triggerRef}
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
        className={cn(
          "flex items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm",
          "hover:bg-surface-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring",
        )}
      >
        <span
          aria-hidden="true"
          className="flex size-7 shrink-0 items-center justify-center rounded-full bg-primary text-xs font-semibold text-primary-foreground"
        >
          {initials(fullName)}
        </span>
        <span className="hidden min-w-0 flex-col leading-tight sm:flex">
          <span className="truncate font-medium text-foreground">{fullName}</span>
          <span className="truncate text-xs text-foreground-muted">{formatRoleLabel(role)}</span>
        </span>
        <ChevronDown className="size-4 shrink-0 text-foreground-muted" aria-hidden="true" />
      </button>

      {open && (
        <ul
          role="menu"
          aria-label="User menu"
          className="absolute right-0 z-20 mt-1 w-56 rounded-md border border-border bg-surface-raised py-1 shadow-lg"
        >
          <li className="flex items-center gap-2 px-3 py-2 text-xs text-foreground-muted" role="none">
            <User className="size-3.5 shrink-0" aria-hidden="true" />
            <span className="truncate">{email}</span>
          </li>
          <li role="none" className="my-1 border-t border-border" />
          <li role="none">
            <button
              ref={registerItem(0)}
              role="menuitem"
              type="button"
              onKeyDown={handleItemKeyDown}
              onClick={handleSignOut}
              disabled={signingOut}
              className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-danger hover:bg-danger-surface focus-visible:outline-none focus-visible:bg-danger-surface disabled:opacity-60"
            >
              <LogOut className="size-4 shrink-0" aria-hidden="true" />
              {signingOut ? "Signing out…" : "Sign out"}
            </button>
          </li>
        </ul>
      )}
    </div>
  );
}

function initials(fullName: string): string {
  const parts = fullName.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
}
