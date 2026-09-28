import type { ReactNode } from "react";
import { AlertTriangle, CheckCircle2, Info, XCircle } from "lucide-react";

import { cn } from "@/lib/cn";

type Tone = "danger" | "warning" | "success" | "info";

const TONE_CLASSES: Record<Tone, string> = {
  danger: "bg-danger-surface border-danger-border text-danger",
  warning: "bg-warning-surface border-warning-border text-warning",
  success: "bg-success-surface border-success-border text-success",
  info: "bg-info-surface border-info-border text-info",
};

const TONE_ICONS: Record<Tone, typeof Info> = {
  danger: XCircle,
  warning: AlertTriangle,
  success: CheckCircle2,
  info: Info,
};

export interface AlertProps {
  tone: Tone;
  title: string;
  children?: ReactNode;
  className?: string;
}

/**
 * Status must never be color-only (persona principle "Status design") — every
 * Alert pairs an icon with a label, and `role="alert"` (or "status" for the
 * non-urgent `info`/`success` tones) so screen readers announce it.
 */
export function Alert({ tone, title, children, className }: AlertProps) {
  const Icon = TONE_ICONS[tone];
  const isUrgent = tone === "danger" || tone === "warning";

  return (
    <div
      role={isUrgent ? "alert" : "status"}
      className={cn("flex gap-3 rounded-lg border px-4 py-3 text-sm", TONE_CLASSES[tone], className)}
    >
      <Icon className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
      <div className="space-y-0.5 text-foreground">
        <p className="font-medium">{title}</p>
        {children && <div className="text-foreground-muted">{children}</div>}
      </div>
    </div>
  );
}
