import { forwardRef } from "react";
import type { ButtonHTMLAttributes } from "react";

import { cn } from "@/lib/cn";
import { Spinner } from "./Spinner";

type Variant = "primary" | "secondary" | "ghost" | "danger";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  loading?: boolean;
}

const VARIANT_CLASSES: Record<Variant, string> = {
  primary:
    "bg-primary text-primary-foreground hover:bg-primary-hover disabled:hover:bg-primary",
  secondary:
    "bg-surface text-foreground border border-border hover:bg-surface-muted",
  ghost: "text-foreground-muted hover:text-foreground hover:bg-surface-muted",
  danger: "bg-danger text-white hover:opacity-90",
};

const BASE_CLASSES =
  "inline-flex items-center justify-center gap-2 rounded-md px-4 py-2 text-sm font-medium " +
  "transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring focus-visible:ring-offset-2 " +
  "disabled:cursor-not-allowed disabled:opacity-60";

/**
 * Shares the Button's visual style with elements that must not be a
 * `<button>` — e.g. a `Link` styled as a primary action (navigating to
 * `/suppliers/new`) — without a second, drifting copy of these classes.
 */
export function buttonClasses(variant: Variant = "primary", className?: string): string {
  return cn(BASE_CLASSES, VARIANT_CLASSES[variant], className);
}

/**
 * The one button primitive the app shell uses. Deliberately small: no size
 * prop yet (nothing in this story needs more than one size) — add variants
 * when a real second use case appears, not preemptively (persona principle
 * "avoid premature abstraction").
 */
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "primary", loading = false, disabled, className, children, ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={buttonClasses(variant, className)}
      {...props}
    >
      {loading && <Spinner className="size-4" />}
      {children}
    </button>
  );
});
