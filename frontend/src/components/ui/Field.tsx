import { forwardRef, useId } from "react";
import type { InputHTMLAttributes, ReactNode } from "react";

import { cn } from "@/lib/cn";

/**
 * The one visual style for text-like controls (inputs, selects, textareas): used by `Field`,
 * `Textarea` and by native `<select>`s so every form control in the app matches.
 */
const CONTROL_BASE =
  "rounded-md border bg-surface text-foreground placeholder:text-foreground-muted " +
  "focus:outline-none focus:ring-2 focus:ring-focus-ring focus:border-focus-ring " +
  "disabled:cursor-not-allowed disabled:opacity-60";

export const controlClasses = `${CONTROL_BASE} border-border-strong px-3 py-1.5 text-sm`;
/** Same control, shortened for table rows and inline toolbars. */
export const compactControlClasses = `${CONTROL_BASE} border-border-strong h-7 px-2 text-xs`;
export const controlInvalidClasses = `${CONTROL_BASE} border-danger px-3 py-1.5 text-sm`;

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
    <div className="space-y-1">
      <label htmlFor={inputId} className="block text-[14px] font-medium text-foreground">
        {label}
      </label>
      <input
        ref={ref}
        id={inputId}
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
