"use client";

import { Badge, TONE_TEXT_CLASSES } from "@/components/ui/Badge";
import { cn } from "@/lib/cn";
import { useI18n } from "@/lib/i18n/client";
import { getStatusDef } from "./status-map";
import type { StatusKind, StatusMap } from "./status-map";

// A Client Component because the label is looked up in the active locale's catalog
// (`useI18n`), which keeps it usable from both Server and Client Components; its props
// (`kind`, `value`, ...) are plain strings, so they cross the boundary fine. The pure data
// (tone, icon, label key) and `statusTone()` live in `./status-map` so Server Components can
// call them directly.

/**
 * The prominent form of a decision (APPROVE / REVIEW / BLOCK): large icon + label in the
 * decision's tone, no pill. Used where the decision IS the page's answer (review results,
 * Decision Passport). Smaller contexts use `StatusBadge kind="decision"`.
 */
export function DecisionMark({
  value,
  caption,
}: {
  value: keyof StatusMap["decision"];
  caption?: string;
}) {
  const { t } = useI18n();
  const { tone, labelKey, icon: Icon } = getStatusDef("decision", value);
  return (
    <div className="flex items-center gap-3">
      {Icon && <Icon className={cn("size-8 shrink-0", TONE_TEXT_CLASSES[tone])} aria-hidden="true" />}
      <div className="leading-tight">
        {caption && <p className="text-xs text-foreground-muted">{caption}</p>}
        <p className={cn("font-serif text-xl font-semibold", TONE_TEXT_CLASSES[tone])}>{t(labelKey)}</p>
      </div>
    </div>
  );
}

/**
 * Renders any domain status as a Badge from the single `STATUS_MAP` (`./status-map`). Icons
 * are rendered here, never passed across the Server->Client boundary.
 */
export function StatusBadge<K extends StatusKind>({
  kind,
  value,
  className,
}: {
  kind: K;
  value: keyof StatusMap[K];
  className?: string;
}) {
  const { t } = useI18n();
  const { tone, labelKey, icon: Icon, spin } = getStatusDef(kind, value);
  return (
    <Badge
      tone={tone}
      className={className}
      icon={
        Icon ? (
          <Icon
            className={spin ? "size-3 motion-safe:animate-spin" : "size-3"}
            aria-hidden="true"
          />
        ) : undefined
      }
    >
      {t(labelKey)}
    </Badge>
  );
}
