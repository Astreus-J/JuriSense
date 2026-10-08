import { cn } from "@/lib/cn";

/**
 * Shared button visual language for the marketing landing page only. Deliberately not the
 * authenticated app's `src/components/ui/Button.tsx` — that primitive is sized and colored for
 * dense in-app chrome, while marketing CTAs need larger touch targets and a couple of
 * surface-specific variants (e.g. a light button that reads correctly on the dark CTA band).
 * This file exists so every CTA across Header/Hero/Plans/CtaSection shares one radius, one
 * focus-ring treatment, and one transition — not five slightly-different inline class strings.
 */

type Size = "sm" | "md" | "lg";

const BASE =
  "inline-flex items-center justify-center gap-2 rounded-lg font-semibold transition-colors " +
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-blue-600";

const SIZES: Record<Size, string> = {
  sm: "px-4 py-2 text-sm",
  md: "px-5 py-2.5 text-sm",
  lg: "px-6 py-3.5 text-base",
};

export function primaryButton(size: Size = "md", className?: string): string {
  return cn(BASE, SIZES[size], "bg-blue-600 text-white hover:bg-blue-700", className);
}

export function secondaryButton(size: Size = "md", className?: string): string {
  return cn(
    BASE,
    SIZES[size],
    "border border-slate-300 text-slate-700 hover:border-blue-600 hover:text-blue-600",
    className,
  );
}

/** For use on dark surfaces (the closing CTA band): a light button reading on navy. */
export function lightButton(size: Size = "md", className?: string): string {
  return cn(
    BASE,
    SIZES[size],
    "bg-white text-slate-900 hover:bg-slate-100 focus-visible:ring-offset-slate-900",
    className,
  );
}
