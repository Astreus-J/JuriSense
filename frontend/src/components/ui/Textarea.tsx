import { forwardRef, useId } from "react";
import type { ReactNode, TextareaHTMLAttributes } from "react";

import { cn } from "@/lib/cn";
import { controlClasses, controlInvalidClasses } from "./Field";

export interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label: string;
  error?: string;
  hint?: ReactNode;
}

/**
 * A labeled multi-line text input, mirroring `Field`'s exact styling/accessibility
 * pattern (label, `aria-describedby`/`aria-invalid`, error/hint) for the one case `Field`
 * can't cover — multi-line content (first needed by `RuleForm`'s rule YAML). Status is
 * never color-only here either (persona: "Never communicate status by color alone"): the
 * error message is always text, never just a red border.
 */
export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(function Textarea(
  { label, error, hint, id, className, rows = 6, ...props },
  ref,
) {
  const generatedId = useId();
  const textareaId = id ?? generatedId;
  const errorId = error ? `${textareaId}-error` : undefined;
  const hintId = hint ? `${textareaId}-hint` : undefined;

  return (
    <div className="space-y-1">
      <label htmlFor={textareaId} className="block text-[14px] font-medium text-foreground">
        {label}
      </label>
      <textarea
        ref={ref}
        id={textareaId}
        rows={rows}
        aria-invalid={Boolean(error) || undefined}
        aria-describedby={cn(errorId, hintId) || undefined}
        className={cn(
          "w-full",
          error ? controlInvalidClasses : controlClasses,
          className,
        )}
        {...props}
      />
      {hint && !error && (
        <p id={hintId} className="text-xs text-foreground-muted">
          {hint}
        </p>
      )}
      {error && (
        <p id={errorId} className="text-xs font-medium text-danger">
          {error}
        </p>
      )}
    </div>
  );
});
