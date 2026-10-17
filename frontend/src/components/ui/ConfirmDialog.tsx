"use client";

import { useEffect, useId, useRef } from "react";
import type { ReactNode } from "react";

import { useI18n } from "@/lib/i18n/client";
import { Button } from "./Button";

export interface ConfirmDialogProps {
  open: boolean;
  title: string;
  /** What will happen and whether it can be undone. */
  children: ReactNode;
  confirmLabel: string;
  cancelLabel?: string;
  /** `danger` for destructive/irreversible actions. */
  tone?: "primary" | "danger";
  loading?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

/**
 * Proportionate confirmation built on the native <dialog> element: showModal() gives us
 * focus trapping, Escape-to-close, an inert background and focus restoration to the trigger
 * for free. Use it only for consequential actions (rejecting an approval, publishing a policy
 * version), never for reversible minor ones.
 */
export function ConfirmDialog({
  open,
  title,
  children,
  confirmLabel,
  cancelLabel,
  tone = "primary",
  loading = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const { t } = useI18n();
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = useId();

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  return (
    <dialog
      ref={ref}
      aria-labelledby={titleId}
      // Native Escape fires `cancel`; route it through our state so `open` stays in sync.
      onCancel={(event) => {
        event.preventDefault();
        if (!loading) onCancel();
      }}
      className="m-auto w-[calc(100%-2rem)] max-w-md rounded-lg border border-border bg-surface-raised p-0 text-foreground shadow-xl"
    >
      <div className="space-y-2 p-5">
        <h2 id={titleId} className="text-base font-semibold text-foreground">
          {title}
        </h2>
        <div className="text-sm text-foreground-muted">{children}</div>
      </div>
      <div className="flex justify-end gap-2 border-t border-border bg-surface-muted px-5 py-3">
        <Button type="button" variant="secondary" onClick={onCancel} disabled={loading}>
          {cancelLabel ?? t("common.cancel")}
        </Button>
        <Button
          type="button"
          variant={tone === "danger" ? "danger" : "primary"}
          onClick={onConfirm}
          loading={loading}
        >
          {confirmLabel}
        </Button>
      </div>
    </dialog>
  );
}
