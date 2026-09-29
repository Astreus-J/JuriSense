import Link from "next/link";
import { SearchX } from "lucide-react";

import { buttonClasses } from "@/components/ui/Button";

/**
 * Rendered when `getSupplier()` 404s in `[id]/page.tsx` (via `notFound()`) — either the
 * supplier doesn't exist, or it belongs to a different organization (the API returns the
 * same 404 for both, so this page doesn't distinguish them either — doing so would leak
 * cross-tenant existence).
 */
export default function SupplierNotFound() {
  return (
    <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-border bg-surface px-6 py-16 text-center">
      <div className="flex size-12 items-center justify-center rounded-full bg-surface-muted">
        <SearchX className="size-6 text-foreground-muted" aria-hidden="true" />
      </div>
      <h1 className="text-lg font-semibold text-foreground">Supplier not found</h1>
      <p className="max-w-sm text-sm text-foreground-muted">
        This supplier doesn&apos;t exist, or isn&apos;t part of your organization.
      </p>
      <Link href="/suppliers" className={buttonClasses("secondary", "mt-1")}>
        Back to suppliers
      </Link>
    </div>
  );
}
