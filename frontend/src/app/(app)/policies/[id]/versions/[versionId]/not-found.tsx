import Link from "next/link";
import { SearchX } from "lucide-react";

import { buttonClasses } from "@/components/ui/Button";

/**
 * Rendered when the policy or the policy version 404s in this segment's `page.tsx` (via
 * `notFound()`) — matching `policies/[id]/not-found.tsx`'s identical reasoning for not
 * distinguishing "no such policy" from "no such version" from "wrong organization".
 */
export default function PolicyVersionNotFound() {
  return (
    <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-border bg-surface px-6 py-16 text-center">
      <div className="flex size-12 items-center justify-center rounded-full bg-surface-muted">
        <SearchX className="size-6 text-foreground-muted" aria-hidden="true" />
      </div>
      <h1 className="text-lg font-semibold text-foreground">Policy version not found</h1>
      <p className="max-w-sm text-sm text-foreground-muted">
        This policy version doesn&apos;t exist, or isn&apos;t part of your organization.
      </p>
      <Link href="/policies" className={buttonClasses("secondary", "mt-1")}>
        Back to policies
      </Link>
    </div>
  );
}
