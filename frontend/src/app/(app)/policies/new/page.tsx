import type { Metadata } from "next";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import { CreatePolicyForm } from "@/components/policies/CreatePolicyForm";
import { requireSession } from "@/lib/auth/session";

export const metadata: Metadata = { title: "Create policy — JuriSense Gate" };

/**
 * A dedicated route rather than a modal (persona: "Do not over-design" — a one-field form
 * doesn't need a modal's focus-trap/overlay machinery, and a route gives it its own URL
 * and back-button behavior, matching `suppliers/new`'s identical reasoning).
 *
 * No role gate here beyond authentication, for the same reason `suppliers/new` has none:
 * a role's default `create` permission is only a UI hint (`getPolicyPermissions`) a
 * per-user override can widen, so this page stays reachable and lets the real 403 from
 * `POST /api/policies` (surfaced by `CreatePolicyForm`) be the authoritative answer — the
 * list page already hides the "Create policy" entry point for roles the default grid
 * says can't create.
 */
export default async function NewPolicyPage() {
  await requireSession();

  return (
    <div className="max-w-lg space-y-6">
      <Link
        href="/policies"
        className="inline-flex items-center gap-1 text-sm font-medium text-foreground-muted hover:text-foreground"
      >
        <ArrowLeft className="size-4" aria-hidden="true" />
        Back to policies
      </Link>

      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Create a policy</h1>
        <p className="mt-1 text-sm text-foreground-muted">
          JuriSense creates its first draft version automatically — you&apos;ll add rules
          to it next, then publish when it&apos;s ready to apply to compliance reviews.
        </p>
      </div>

      <CreatePolicyForm />
    </div>
  );
}
