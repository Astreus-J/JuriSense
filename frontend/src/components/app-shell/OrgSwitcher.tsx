"use client";

import { Building2, Check, ChevronsUpDown } from "lucide-react";

import { cn } from "@/lib/cn";
import type { Membership } from "@/lib/auth/types";
import { useDropdownMenu } from "./useDropdownMenu";

interface OrgSwitcherProps {
  memberships: Membership[];
  activeOrganizationId: string;
}

/**
 * Renders as a real menu-button widget (WAI-ARIA Menu Button pattern) even
 * though `GET /api/auth/me` returns exactly one organization per user today
 * — STORY-1.2.1 requires the switcher to already work once a user holds more
 * than one `Membership` (`docs/03-domain/domain-model.md`), so this must not
 * be a static label that gets rebuilt later.
 *
 * Known gap (flagged, not invented around): `UserResponse` has no
 * organization *name* field, only `organization_id` — see
 * `backend/app/identity/api/schemas.py`. Until a future API change exposes
 * one, this falls back to a short, clearly-labeled id so it never displays a
 * fabricated name.
 */
export function OrgSwitcher({ memberships, activeOrganizationId }: OrgSwitcherProps) {
  const { open, setOpen, containerRef, triggerRef, registerItem, handleItemKeyDown } =
    useDropdownMenu();

  const active =
    memberships.find((m) => m.organizationId === activeOrganizationId) ?? memberships[0];

  return (
    <div ref={containerRef} className="relative">
      <button
        ref={triggerRef}
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
        className={cn(
          "flex w-full items-center gap-2 rounded-md border border-border bg-surface px-3 py-2 text-left text-sm",
          "hover:bg-surface-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring",
        )}
      >
        <Building2 className="size-4 shrink-0 text-foreground-muted" aria-hidden="true" />
        <span className="min-w-0 flex-1 truncate font-medium text-foreground">
          {formatOrgLabel(active)}
        </span>
        {memberships.length > 1 && (
          <ChevronsUpDown className="size-4 shrink-0 text-foreground-muted" aria-hidden="true" />
        )}
      </button>

      {open && (
        <ul
          role="menu"
          aria-label="Switch organization"
          className="absolute left-0 z-20 mt-1 w-full min-w-[14rem] rounded-md border border-border bg-surface-raised py-1 shadow-lg"
        >
          {memberships.map((membership, index) => (
            <li key={membership.organizationId} role="none">
              <button
                ref={registerItem(index)}
                role="menuitem"
                type="button"
                onKeyDown={handleItemKeyDown}
                onClick={() => setOpen(false)}
                className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-foreground hover:bg-surface-muted focus-visible:outline-none focus-visible:bg-surface-muted"
              >
                <Check
                  className={cn(
                    "size-4 shrink-0",
                    membership.organizationId === active.organizationId
                      ? "text-primary"
                      : "text-transparent",
                  )}
                  aria-hidden="true"
                />
                <span className="truncate">{formatOrgLabel(membership)}</span>
              </button>
            </li>
          ))}
          {memberships.length === 1 && (
            <li className="border-t border-border px-3 pt-2 pb-1 text-xs text-foreground-muted">
              You&apos;re only a member of this organization.
            </li>
          )}
        </ul>
      )}
    </div>
  );
}

function formatOrgLabel(membership: Membership): string {
  if (membership.organizationName) return membership.organizationName;
  return `Organization ${membership.organizationId.slice(0, 8)}`;
}
