import Link from "next/link";
import { SearchX } from "lucide-react";

import { buttonClasses } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";

/**
 * Rendered when `getPolicy()` 404s in `[id]/page.tsx` (via `notFound()`) — either the
 * policy doesn't exist, or it belongs to a different organization (the API returns the
 * same 404 for both, so this page doesn't distinguish them either, matching
 * `suppliers/[id]/not-found.tsx`'s identical reasoning — doing so would leak cross-tenant
 * existence).
 */
export default function PolicyNotFound() {
  return (
    <EmptyState
      as="h1"
      icon={SearchX}
      title="Policy not found"
      description={<>This policy doesn&apos;t exist, or isn&apos;t part of your organization.</>}
      action={
        <Link href="/policies" className={buttonClasses("secondary")}>
          Back to policies
        </Link>
      }
    />
  );
}
