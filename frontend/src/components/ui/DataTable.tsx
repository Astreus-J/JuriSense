import Link from "next/link";
import type { ComponentProps, ReactNode, TdHTMLAttributes, ThHTMLAttributes } from "react";

import { cn } from "@/lib/cn";

/**
 * Table primitives for dense, scannable lists. Server-component friendly (no state).
 *
 *   <DataTable caption="Suppliers">
 *     <thead><tr><Th>Legal name</Th>...</tr></thead>
 *     <tbody><Tr><Td><RowLink href=...>Acme</RowLink></Td>...</Tr></tbody>
 *   </DataTable>
 *
 * - The caption is screen-reader only (the page's `<h1>`/section title is the visible label).
 * - Headers always carry `scope="col"`.
 * - Rows get a hover tint; `RowLink` stretches its anchor over the whole row so the entire
 *   row is the click/tap target while keeping a single, keyboard-focusable link.
 * - Numeric/date columns: pass `numeric` to right-align with tabular figures.
 */
export function DataTable({
  caption,
  children,
  className,
}: {
  caption: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("overflow-x-auto rounded-lg border border-border bg-surface", className)}>
      <table className="w-full min-w-max border-collapse text-left text-sm">
        <caption className="sr-only">{caption}</caption>
        {children}
      </table>
    </div>
  );
}

export function Th({
  numeric,
  className,
  ...props
}: ThHTMLAttributes<HTMLTableCellElement> & { numeric?: boolean }) {
  return (
    <th
      scope="col"
      className={cn(
        "border-b border-border bg-surface-muted px-3 py-2 text-xs font-medium text-foreground-muted",
        numeric && "text-right",
        className,
      )}
      {...props}
    />
  );
}

export function Tr({ className, ...props }: ComponentProps<"tr">) {
  return (
    <tr
      className={cn(
        "relative border-b border-border last:border-b-0 hover:bg-surface-muted focus-within:bg-surface-muted",
        className,
      )}
      {...props}
    />
  );
}

export function Td({
  numeric,
  muted,
  className,
  ...props
}: TdHTMLAttributes<HTMLTableCellElement> & { numeric?: boolean; muted?: boolean }) {
  return (
    <td
      className={cn(
        "px-3 py-2 align-middle",
        muted && "text-foreground-muted",
        numeric && "text-right tabular-nums",
        className,
      )}
      {...props}
    />
  );
}

/** The primary link of a row; its ::after covers the row (the `Tr` is `relative`). */
export function RowLink({ className, ...props }: ComponentProps<typeof Link>) {
  return (
    <Link
      className={cn(
        "font-medium text-foreground hover:underline focus-visible:outline-none",
        "after:absolute after:inset-0 after:content-[''] focus-visible:after:ring-2 focus-visible:after:ring-inset focus-visible:after:ring-focus-ring",
        className,
      )}
      {...props}
    />
  );
}
