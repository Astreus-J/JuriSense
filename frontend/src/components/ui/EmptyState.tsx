import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";

import { cn } from "@/lib/cn";

export interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  /** What is empty, why, and what the user can do next. */
  description?: ReactNode;
  action?: ReactNode;
  /** Heading level: `h2` by default (the page `<h1>` lives in PageHeader); `h1` for standalone
   * pages with no PageHeader, such as not-found screens. */
  as?: "h1" | "h2";
  className?: string;
}

/**
 * Empty / zero-results / no-access states. Intentionally quiet: a dashed outline, a small
 * icon and a short instruction -- the next action is the only emphasized element.
 */
export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  as: Heading = "h2",
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center gap-2 rounded-lg border border-dashed border-border-strong px-6 py-12 text-center",
        className,
      )}
    >
      {Icon && <Icon className="size-5 text-foreground-muted" aria-hidden="true" />}
      <Heading className="text-sm font-semibold text-foreground">{title}</Heading>
      {description && <p className="max-w-md text-sm text-foreground-muted">{description}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}
