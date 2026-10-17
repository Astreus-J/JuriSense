import { PageHeader } from "@/components/ui/PageHeader";
import { CreateSupplierForm } from "@/components/suppliers/CreateSupplierForm";
import { requireSession } from "@/lib/auth/session";
import { getI18n, pageTitle } from "@/lib/i18n/server";

export const generateMetadata = pageTitle("meta.supplierNew");

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
  const { t } = await getI18n();

  return (
    <div className="max-w-lg space-y-5">
      <PageHeader
        breadcrumbs={[
          { label: t("nav.suppliers"), href: "/suppliers" },
          { label: t("suppliers.new.breadcrumb") },
        ]}
        title={t("suppliers.new.title")}
        description={t("suppliers.new.description")}
      />
      <CreateSupplierForm />
    </div>
  );
}
