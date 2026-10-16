import Link from "next/link";
import { SearchX } from "lucide-react";

import { buttonClasses } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";

/**
 * Rendered when `getDecisionPassport()` 404s in `[id]/page.tsx` (via `notFound()`) — a
 * missing Decision, one in another organization, and one with no EvidencePackage yet all
 * collapse to the same 404 (ADR-003), so this page doesn't distinguish them either.
 */
export default function DecisionPassportNotFound() {
  return (
    <EmptyState
      as="h1"
      icon={SearchX}
      title="Decision not found"
      description={<>This decision doesn&apos;t exist, isn&apos;t part of your organization, or has no evidence
        package yet.</>}
      action={
        <Link href="/evidence" className={buttonClasses("secondary")}>
          Back to Evidence & Audit
        </Link>
      }
    />
  );
}
