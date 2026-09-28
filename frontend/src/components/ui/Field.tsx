import { forwardRef, useId } from "react";
import type { InputHTMLAttributes, ReactNode } from "react";

import { cn } from "@/lib/cn";

export interface FieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string;
  hint?: ReactNode;
}

/**
 * A labeled text input with an associated error message (`aria-describedby` +
 * `aria-invalid`), so assistive tech announces validation state the same way
 * sighted users see it (persona: "Never communicate status by color alone").
 */
export const Field = forwardRef<HTMLInputElement, FieldProps>(function Field(
  { label, error, hint, id, className, ...props },
  ref,
) {
  const generatedId = useId();
  const inputId = id ?? generatedId;
  const errorId = error ? `${inputId}-error` : undefined;
  const hintId = hint ? `${inputId}-hint` : undefined;

  return (
    <div className="space-y-1.5">
      <label htmlFor={inputId} className="block text-sm font-medium text-foreground">
        {label}
      </label>
      <input
        ref={ref}
        id={inputId}
        aria-invalid={Boolean(error) || undefined}
        aria-describedby={cn(errorId, hintId) || undefined}
        className={cn(
          "w-full rounded-md border bg-surface px-3 py-2 text-sm text-foreground shadow-sm",
          "placeholder:text-foreground-muted",
          "focus:outline-none focus:ring-2 focus:ring-focus-ring focus:border-transparent",
          error ? "border-danger" : "border-border",
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
