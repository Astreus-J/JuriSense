import Link from "next/link";
import { Plus } from "lucide-react";

import { Alert } from "@/components/ui/Alert";
import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { buttonClasses } from "@/components/ui/Button";
import { PolicyTable } from "@/components/policies/PolicyTable";
import { ApiError } from "@/lib/auth/backend";
import { readAccessToken } from "@/lib/auth/cookies";
import { requireSession } from "@/lib/auth/session";
import { getI18n, pageTitle } from "@/lib/i18n/server";
import { NAV_ITEMS } from "@/lib/navigation/modules";
import { listPolicies } from "@/lib/policies/backend";
import { getPolicyPermissions } from "@/lib/policies/permissions";

export const generateMetadata = pageTitle("meta.policies");

export default async function PoliciesPage() {
  const user = await requireSession();
  const { t } = await getI18n();
  const permissions = getPolicyPermissions(user.role);

  const accessToken = await readAccessToken();
  let policies: Awaited<ReturnType<typeof listPolicies>> = [];
  let forbidden = false;

  try {
    // `requireSession()` above already guarantees a valid token exists; the `!` mirrors
    // the same non-null assumption `suppliers/page.tsx` makes right after its own read.
    policies = await listPolicies(accessToken!);
  } catch (error) {
    if (error instanceof ApiError && error.status === 403) {
      forbidden = true;
    } else {
      // Anything else (5xx, network) is a real failure — let the segment's error.tsx handle it.
      throw error;
    }
  }

  return (
    <div className="space-y-5">
      <PageHeader
        title={t("nav.policies")}
        description={t("policies.list.description")}
        actions={
          !forbidden && permissions.canCreate ? (
            <Link href="/policies/new" className={buttonClasses("primary")}>
              <Plus className="size-4" aria-hidden="true" />
              {t("policies.list.create")}
            </Link>
          ) : undefined
        }
      />

      {forbidden ? (
        <Alert tone="danger" title={t("policies.list.forbiddenTitle")}>
          {t("policies.list.forbiddenBody")}
        </Alert>
      ) : policies.length === 0 ? (
        <PoliciesEmptyState canCreate={permissions.canCreate} />
      ) : (
        <PolicyTable policies={policies} />
      )}
    </div>
  );
}

async function PoliciesEmptyState({ canCreate }: { canCreate: boolean }) {
  const { t } = await getI18n();
  return (
    <EmptyState
      icon={NAV_ITEMS.policies.icon}
      title={t("policies.list.emptyTitle")}
      description={t("policies.list.emptyBody")}
      action={
        canCreate ? (
          <Link href="/policies/new" className={buttonClasses("primary")}>
            <Plus className="size-4" aria-hidden="true" />
            {t("policies.list.create")}
          </Link>
        ) : undefined
      }
    />
  );
}
