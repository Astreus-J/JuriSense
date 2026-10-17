import { StatusBadge } from "@/components/shared/StatusBadge";
import { notFound } from "next/navigation";

import { Alert } from "@/components/ui/Alert";
import { PageHeader } from "@/components/ui/PageHeader";
import { CreateDraftVersionButton } from "@/components/policies/CreateDraftVersionButton";
import { PolicyVersionList } from "@/components/policies/PolicyVersionList";
import { ApiError } from "@/lib/auth/backend";
import { readAccessToken } from "@/lib/auth/cookies";
import { requireSession } from "@/lib/auth/session";
import { formatDateTime } from "@/lib/format";
import { getI18n, pageTitle } from "@/lib/i18n/server";
import { getPolicy, listPolicyVersions } from "@/lib/policies/backend";
import { getPolicyPermissions } from "@/lib/policies/permissions";

export const generateMetadata = pageTitle("meta.policy");

interface PolicyDetailPageProps {
  // Next 16: `params` is a Promise (see `node_modules/next/dist/docs/01-app/
  // 03-api-reference/03-file-conventions/page.md`).
  params: Promise<{ id: string }>;
}

export default async function PolicyDetailPage({ params }: PolicyDetailPageProps) {
  const user = await requireSession();
  const { t, locale } = await getI18n();
  const breadcrumbs = [
    { label: t("nav.policies"), href: "/policies" },
    { label: t("policies.detail.breadcrumb") },
  ];
  const { id } = await params;
  const accessToken = (await readAccessToken())!;
  const permissions = getPolicyPermissions(user.role);

  let policy;
  try {
    policy = await getPolicy(accessToken, id);
  } catch (error) {
    // A malformed id (not a UUID) is treated the same as "no such policy" -- there's no
    // useful distinction to surface to the user, matching `suppliers/[id]/page.tsx`'s
    // identical note.
    if (error instanceof ApiError && (error.status === 404 || error.status === 400)) notFound();
    if (error instanceof ApiError && error.status === 403) {
      return (
        <div className="space-y-5">
          <PageHeader title={t("policies.detail.breadcrumb")} breadcrumbs={breadcrumbs} />
          <Alert tone="danger" title={t("policies.detail.noAccessTitle")}>
            {t("policies.detail.noAccessBody")}
          </Alert>
        </div>
      );
    }
    throw error;
  }

  const versions = await listPolicyVersions(accessToken, id);

  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumbs={[breadcrumbs[0], { label: policy.name }]}
        title={policy.name}
        meta={
          <>
            <StatusBadge kind="policy" value={policy.status} />
            <span className="text-sm tabular-nums text-foreground-muted">
              {t("policies.detail.created", { date: formatDateTime(policy.createdAt, locale) })}
            </span>
          </>
        }
        actions={permissions.canCreate ? <CreateDraftVersionButton policyId={policy.id} /> : undefined}
      />

      <section className="space-y-3">
        <h2 className="text-base font-semibold text-foreground">{t("policies.detail.versions")}</h2>
        {versions.length === 0 ? (
          // A Policy is only ever created together with its first draft version
          // (`policy_service.create_policy`) — this is a defensive branch for an
          // invariant that should never actually break, not an expected empty state.
          <Alert tone="warning" title={t("policies.detail.noVersionsTitle")}>
            {t("policies.detail.noVersionsBody")}
          </Alert>
        ) : (
          <PolicyVersionList policyId={policy.id} versions={versions} />
        )}
      </section>
    </div>
  );
}
