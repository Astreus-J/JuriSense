import Link from "next/link";
import type { ReactNode } from "react";
import { ChevronRight } from "lucide-react";

import { cn } from "@/lib/cn";
import { getI18n } from "@/lib/i18n/server";

export interface Breadcrumb {
  label: string;
  /** Omit for the current page (rendered as plain text with aria-current). */
  href?: string;
}

export interface PageHeaderProps {
  /** The page's single `<h1>`. */
  title: ReactNode;
  description?: ReactNode;
  /** Status tags, identifiers and other metadata shown right under the title. */
  meta?: ReactNode;
  /** Primary/secondary page actions, right-aligned on wide screens. */
  actions?: ReactNode;
  breadcrumbs?: Breadcrumb[];
  className?: string;
}

/**
 * Every authenticated page renders exactly one of these: it owns the page's only `<h1>`,
 * the optional breadcrumb trail, and the page-level actions. Titles use the serif face so
 * the page identity is carried by typography rather than by decoration.
 */
export async function PageHeader({
  title,
  description,
  meta,
  actions,
  breadcrumbs,
  className,
}: PageHeaderProps) {
  const { t } = await getI18n();
  return (
    <header className={cn("space-y-2 border-b border-border pb-4", className)}>
      {breadcrumbs && breadcrumbs.length > 0 && (
        <nav aria-label={t("common.breadcrumb")}>
          <ol className="flex flex-wrap items-center gap-1 text-xs text-foreground-muted">
            {breadcrumbs.map((crumb, index) => {
              const isLast = index === breadcrumbs.length - 1;
              return (
                <li key={`${crumb.label}-${index}`} className="flex items-center gap-1">
                  {crumb.href && !isLast ? (
                    <Link
                      href={crumb.href}
                      className="rounded hover:text-foreground hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring"
                    >
                      {crumb.label}
                    </Link>
                  ) : (
                    <span aria-current={isLast ? "page" : undefined}>{crumb.label}</span>
                  )}
                  {!isLast && <ChevronRight className="size-3" aria-hidden="true" />}
                </li>
              );
            })}
          </ol>
        </nav>
      )}
      <div className="flex flex-wrap items-start justify-between gap-x-6 gap-y-3">
        <div className="min-w-0 space-y-1">
          <h1 className="font-serif text-2xl font-semibold leading-tight tracking-tight text-foreground">
            {title}
          </h1>
          {description && (
            <p className="max-w-2xl text-sm text-foreground-muted">{description}</p>
          )}
        </div>
        {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
      </div>
      {meta && <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5">{meta}</div>}
    </header>
  );
}
