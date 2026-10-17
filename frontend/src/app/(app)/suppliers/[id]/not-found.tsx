import Link from "next/link";
import { SearchX } from "lucide-react";

import { buttonClasses } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";

/**
 * Rendered when `getSupplier()` 404s in `[id]/page.tsx` (via `notFound()`) — either the
 * supplier doesn't exist, or it belongs to a different organization (the API returns the
 * same 404 for both, so this page doesn't distinguish them either — doing so would leak
 * cross-tenant existence).
 */
export default function SupplierNotFound() {
  return (
    <EmptyState
      as="h1"
      icon={SearchX}
      title="Supplier not found"
      description={<>This supplier doesn&apos;t exist, or isn&apos;t part of your organization.</>}
      action={
        <Link href="/suppliers" className={buttonClasses("secondary")}>
          Back to suppliers
        </Link>
      }
    />
  );
}
