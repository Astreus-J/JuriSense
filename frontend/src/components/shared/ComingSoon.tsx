import type { LucideIcon } from "lucide-react";

import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { getI18n } from "@/lib/i18n/server";

interface ComingSoonProps {
  icon: LucideIcon;
  title: string;
  description: string;
}

/**
 * Placeholder for a module's real screens that don't exist yet. Still follows the empty-state
 * standard: says what this section is for and what will appear here, instead of a bare
 * "Coming soon." Owns the page's `<h1>` through `PageHeader`.
 */
export async function ComingSoon({ icon, title, description }: ComingSoonProps) {
  const { t } = await getI18n();
  return (
    <div className="space-y-5">
      <PageHeader title={title} description={description} />
      <EmptyState
        icon={icon}
        title={t("errors.notAvailableYet")}
        description={t("errors.notAvailableYetDescription")}
      />
    </div>
  );
}
