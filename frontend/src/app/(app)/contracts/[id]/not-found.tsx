import Link from "next/link";
import { SearchX } from "lucide-react";

import { buttonClasses } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";

/**
 * Rendered when `getContract()` 404s in `[id]/page.tsx` (via `notFound()`) — either the
 * contract doesn't exist, or it belongs to a different organization (the API returns the
 * same 404 for both, so this page doesn't distinguish them either — doing so would leak
 * cross-tenant existence, same rationale as `suppliers/[id]/not-found.tsx`).
 */
export default function ContractNotFound() {
  return (
    <EmptyState
      as="h1"
      icon={SearchX}
      title="Contract not found"
      description={<>This contract doesn&apos;t exist, or isn&apos;t part of your organization.</>}
      action={
        <Link href="/contracts" className={buttonClasses("secondary")}>
          Back to contracts
        </Link>
      }
    />
  );
}
