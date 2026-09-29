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

export interface BadgeProps {
  tone: BadgeTone;
  icon?: ReactNode;
  children: ReactNode;
  className?: string;
}

/**
 * Small status pill — the first Badge primitive in this design system (Suppliers is the
 * first screen that needs one). Status is never color-only (persona: "Never communicate
 * status by color alone"): pair a tone with a label, and optionally an icon.
 */
export function Badge({ tone, icon, children, className }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium",
        TONE_CLASSES[tone],
        className,
      )}
    >
      {icon}
      {children}
    </span>
  );
}
