import type { Metadata } from "next";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import { CreateSupplierForm } from "@/components/suppliers/CreateSupplierForm";
import { requireSession } from "@/lib/auth/session";

export const metadata: Metadata = { title: "Register supplier — JuriSense Gate" };

/**
 * A dedicated route rather than a modal (persona: "Do not over-design" — a three-field
 * form doesn't need a modal's focus-trap/overlay machinery, and a route gives it its own
 * URL, back-button behavior, and a natural place to redirect to after success). Story #32's
 * own acceptance criteria only covers list/detail screens; this form exists to make
 * EPIC-2's "Procurement registers a Supplier with a CNPJ" criterion actually usable end to
 * end — see the Plane comment on #32.
 *
 * No role gate here beyond authentication: a role's default `create` permission is only a
 * UI hint (`getSupplierPermissions`) that a per-user override can widen, so this page stays
 * reachable and lets the real 403 from `POST /api/suppliers` (surfaced by
 * `CreateSupplierForm`) be the authoritative answer — the list page already hides the
 * "Register supplier" entry point for roles the default grid says can't create.
 */
export default async function NewSupplierPage() {
  await requireSession();

  return (
    <div className="max-w-lg space-y-6">
      <Link
        href="/suppliers"
        className="inline-flex items-center gap-1 text-sm font-medium text-foreground-muted hover:text-foreground"
      >
        <ArrowLeft className="size-4" aria-hidden="true" />
        Back to suppliers
      </Link>

      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">
          Register a supplier
        </h1>
        <p className="mt-1 text-sm text-foreground-muted">
          JuriSense automatically starts a verification check against official and public
          sources as soon as the supplier is registered.
        </p>
      </div>

      <CreateSupplierForm />
    </div>
  );
}
