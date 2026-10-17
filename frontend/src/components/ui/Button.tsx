import { forwardRef } from "react";
import type { ButtonHTMLAttributes } from "react";

import { cn } from "@/lib/cn";
import { Spinner } from "./Spinner";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "sm" | "md";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
}

const VARIANT_CLASSES: Record<Variant, string> = {
  primary:
    "bg-primary text-primary-foreground hover:bg-primary-hover disabled:hover:bg-primary",
  secondary:
    "bg-surface text-foreground border border-border-strong hover:bg-surface-muted",
  ghost: "text-foreground-muted hover:text-foreground hover:bg-surface-muted",
  danger: "bg-danger text-white hover:opacity-90",
};

const SIZE_CLASSES: Record<Size, string> = {
  sm: "h-7 px-2.5 text-xs [&_svg]:size-3.5",
  md: "h-9 px-3.5 text-sm",
};

const BASE_CLASSES =
  "inline-flex shrink-0 items-center justify-center gap-1.5 rounded-md font-medium " +
  "transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring focus-visible:ring-offset-2 " +
  "disabled:cursor-not-allowed disabled:opacity-60";

/**
 * Shares the Button's visual style with elements that must not be a
 * `<button>` — e.g. a `Link` styled as a primary action (navigating to
 * `/suppliers/new`) — without a second, drifting copy of these classes.
 */
export function buttonClasses(
  variant: Variant = "primary",
  className?: string,
  size: Size = "md",
): string {
  return cn(BASE_CLASSES, SIZE_CLASSES[size], VARIANT_CLASSES[variant], className);
}

/**
 * The one button primitive. Two sizes: `md` (default, 36px) for page-level actions and
 * forms, `sm` (28px) for dense contexts such as table rows and inline toolbars.
 */
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "primary", size = "md", loading = false, disabled, className, children, ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={buttonClasses(variant, className, size)}
      {...props}
    >
      {loading && <Spinner className="size-3.5" />}
      {children}
    </button>
  );
});
