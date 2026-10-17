import Link from "next/link";
import { SearchX } from "lucide-react";

import { buttonClasses } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";

/**
 * Rendered when the policy or the policy version 404s in this segment's `page.tsx` (via
 * `notFound()`) — matching `policies/[id]/not-found.tsx`'s identical reasoning for not
 * distinguishing "no such policy" from "no such version" from "wrong organization".
 */
export default function PolicyVersionNotFound() {
  return (
    <EmptyState
      as="h1"
      icon={SearchX}
      title="Policy version not found"
      description={<>This policy version doesn&apos;t exist, or isn&apos;t part of your organization.</>}
      action={
        <Link href="/policies" className={buttonClasses("secondary")}>
          Back to policies
        </Link>
      }
    />
  );
}
