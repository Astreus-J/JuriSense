import type { LucideIcon } from "lucide-react";

import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";

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
export function ComingSoon({ icon, title, description }: ComingSoonProps) {
  return (
    <div className="space-y-5">
      <PageHeader title={title} description={description} />
      <EmptyState
        icon={icon}
        title="Not available yet"
        description="This area is being built. Nothing needs to be configured on your side in the meantime."
      />
    </div>
  );
}
