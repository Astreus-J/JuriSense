import type { Metadata } from "next";
import { PageHeader } from "@/components/ui/PageHeader";
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
    <div className="max-w-lg space-y-5">
      <PageHeader
        breadcrumbs={[{ label: "Policies", href: "/policies" }, { label: "Create policy" }]}
        title="Create a policy"
        description="JuriSense creates its first draft version automatically. You'll add rules to it next, then publish when it's ready to apply to compliance reviews."
      />
      <CreatePolicyForm />
    </div>
  );
}
