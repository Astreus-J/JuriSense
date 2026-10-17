import { Building2 } from "lucide-react";

import { getI18n } from "@/lib/i18n/server";
import type { Membership } from "@/lib/auth/types";

interface OrgSwitcherProps {
  memberships: Membership[];
  activeOrganizationId: string;
}

/**
 * Shows the active organization. It is deliberately NOT an interactive control: there is no
 * organization-switching API yet (`GET /api/auth/me` returns exactly one organization per
 * user, and nothing in the BFF can change the session's organization), so a button here
 * would be a dead control. When switching ships, this is the one place to turn into a menu.
 *
 * `UserResponse` also carries no organization *name*, only `organization_id`, so this falls
 * back to a short, clearly-labeled id rather than displaying a fabricated name.
 */
export async function OrgSwitcher({ memberships, activeOrganizationId }: OrgSwitcherProps) {
  const { t } = await getI18n();
  const active =
    memberships.find((m) => m.organizationId === activeOrganizationId) ?? memberships[0];
  const label = active.organizationName || t("shell.organizationFallback", { id: active.organizationId.slice(0, 8) });

  return (
    <div className="flex items-center gap-2 rounded-md border border-border bg-surface px-2.5 py-1.5">
      <Building2 className="size-4 shrink-0 text-foreground-muted" aria-hidden="true" />
      <div className="min-w-0 leading-tight">
        <p className="text-[12px] text-foreground-muted">{t("shell.organization")}</p>
        <p className="truncate text-[14px] font-medium text-foreground" title={label}>
          {label}
        </p>
      </div>
    </div>
  );
}
