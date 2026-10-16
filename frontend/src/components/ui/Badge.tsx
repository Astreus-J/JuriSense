import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

export type BadgeTone = "neutral" | "info" | "success" | "warning" | "danger";

const TONE_CLASSES: Record<BadgeTone, string> = {
  neutral: "bg-surface-muted text-foreground-muted border-border",
  info: "bg-info-surface text-info border-info-border",
  success: "bg-success-surface text-success border-success-border",
  warning: "bg-warning-surface text-warning border-warning-border",
  danger: "bg-danger-surface text-danger border-danger-border",
};

/** Left-rail accent for rows/blocks whose state matters (risks, failed rules, decisions). */
export const TONE_RAIL_CLASSES: Record<BadgeTone, string> = {
  neutral: "border-l-border-strong",
  info: "border-l-info",
  success: "border-l-success",
  warning: "border-l-warning",
  danger: "border-l-danger",
};

/** Text color for a tone, for icon+label marks that are not pills. */
export const TONE_TEXT_CLASSES: Record<BadgeTone, string> = {
  neutral: "text-foreground-muted",
  info: "text-info",
  success: "text-success",
  warning: "text-warning",
  danger: "text-danger",
};

export interface BadgeProps {
  tone: BadgeTone;
  icon?: ReactNode;
  children: ReactNode;
  className?: string;
}

/**
 * Compact status tag (square-ish, not a pill: reads as a data label, not a button). Status is never color-only (persona: "Never communicate
 * status by color alone"): pair a tone with a label, and optionally an icon.
 */
export function Badge({ tone, icon, children, className }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 whitespace-nowrap rounded border px-1.5 py-0.5 text-xs font-medium leading-4",
        TONE_CLASSES[tone],
        className,
      )}
    >
      {icon}
      {children}
    </span>
  );
}
