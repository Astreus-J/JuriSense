import type { LucideIcon } from "lucide-react";

interface ComingSoonProps {
  icon: LucideIcon;
  title: string;
  description: string;
}

/**
 * Placeholder for a module's real screens (e.g. Suppliers, Contracts) that
 * don't exist yet — later epics build them (see STORY-1.2.1's scope
 * discipline: this shell only builds nav + placeholders, not feature pages).
 *
 * Still follows the persona's empty-state standard: says what this section
 * is for and what will appear here, instead of a bare "Coming soon."
 */
export function ComingSoon({ icon: Icon, title, description }: ComingSoonProps) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-border bg-surface px-6 py-16 text-center">
      <div className="flex size-12 items-center justify-center rounded-full bg-surface-muted">
        <Icon className="size-6 text-foreground-muted" aria-hidden="true" />
      </div>
      <h1 className="text-lg font-semibold text-foreground">{title}</h1>
      <p className="max-w-sm text-sm text-foreground-muted">{description}</p>
      <span className="mt-1 rounded-full bg-surface-muted px-3 py-1 text-xs font-medium text-foreground-muted">
        Coming soon
      </span>
    </div>
  );
}
