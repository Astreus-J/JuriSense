import { StatusBadge } from "@/components/shared/StatusBadge";
import { notFound } from "next/navigation";

import { Alert } from "@/components/ui/Alert";
import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { AddRuleControl } from "@/components/policies/AddRuleControl";
import { PublishVersionButton } from "@/components/policies/PublishVersionButton";
import { RuleListItem } from "@/components/policies/RuleListItem";
import { ApiError } from "@/lib/auth/backend";
import { readAccessToken } from "@/lib/auth/cookies";
import { requireSession } from "@/lib/auth/session";
import { formatDateTime } from "@/lib/format";
import { getI18n, pageTitle } from "@/lib/i18n/server";
import { getPolicy, getPolicyVersion, listRules } from "@/lib/policies/backend";
import { getPolicyPermissions } from "@/lib/policies/permissions";

export const generateMetadata = pageTitle("meta.policyVersion");

interface PolicyVersionDetailPageProps {
  // Next 16: `params` is a Promise.
  params: Promise<{ id: string; versionId: string }>;
}

export default async function PolicyVersionDetailPage({ params }: PolicyVersionDetailPageProps) {
  const user = await requireSession();
  const { t, locale } = await getI18n();
  const { id, versionId } = await params;
  const accessToken = (await readAccessToken())!;
  const permissions = getPolicyPermissions(user.role);

  let policy;
  let version;
  try {
    // Fetched sequentially, not in parallel: `getPolicyVersion` re-validates the policy
    // itself server-side regardless, but this ordering lets a "policy not found" 404
    // short-circuit before a second request for a version that can't possibly belong to
    // a nonexistent policy — matching the 404-precedence `contracts/[id]/page.tsx` applies.
    policy = await getPolicy(accessToken, id);
    version = await getPolicyVersion(accessToken, id, versionId);
  } catch (error) {
    // A malformed id is treated the same as "not found" -- matching `policies/[id]/
    // page.tsx`'s identical note.
    if (error instanceof ApiError && (error.status === 404 || error.status === 400)) notFound();
    if (error instanceof ApiError && error.status === 403) {
      return (
        <div className="space-y-5">
          <PageHeader
            title={t("policies.version.title")}
            breadcrumbs={[
              { label: t("nav.policies"), href: "/policies" },
              { label: t("policies.detail.breadcrumb"), href: `/policies/${id}` },
              { label: t("policies.version.breadcrumb") },
            ]}
          />
          <Alert tone="danger" title={t("policies.version.noAccessTitle")}>
            {t("policies.version.noAccessBody")}
          </Alert>
        </div>
      );
    }
    throw error;
  }

  const rules = await listRules(accessToken, id, versionId);
  const isDraft = version.status === "draft";
  const canEditRules = isDraft && permissions.canUpdate;
  const canAddRules = isDraft && permissions.canCreate;

  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumbs={[
          { label: t("nav.policies"), href: "/policies" },
          { label: policy.name, href: `/policies/${id}` },
          { label: t("policies.version.breadcrumbVersion", { number: version.versionNumber }) },
        ]}
        title={t("policies.version.pageTitle", { policy: policy.name, number: version.versionNumber })}
        meta={
          <>
            <StatusBadge kind="policyVersion" value={version.status} />
            {version.isCurrent && <span className="text-xs text-foreground-muted">{t("policies.version.current")}</span>}
            <span className="text-sm tabular-nums text-foreground-muted">
              {version.publishedAt
                ? t("policies.version.published", { date: formatDateTime(version.publishedAt, locale) })
                : t("policies.version.created", { date: formatDateTime(version.createdAt, locale) })}
            </span>
          </>
        }
        actions={
          isDraft && permissions.canUpdate ? (
            <PublishVersionButton policyId={id} versionId={versionId} />
          ) : undefined
        }
      />

      {!isDraft && (
        <Alert tone="info" title={t("policies.version.frozenTitle")}>
          {t("policies.version.frozenBody")}
        </Alert>
      )}

      <section className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <h2 className="text-base font-semibold text-foreground">
            {t("policies.version.rules")} <span className="font-normal tabular-nums text-foreground-muted">({rules.length})</span>
          </h2>
          {canAddRules && <AddRuleControl policyId={id} versionId={versionId} />}
        </div>

        {rules.length === 0 ? (
          <RulesEmptyState canAdd={canAddRules} />
        ) : (
          <ul className="space-y-4">
            {rules.map((rule) => (
              <RuleListItem
                key={rule.id}
                policyId={id}
                versionId={versionId}
                rule={rule}
                canEdit={canEditRules}
              />
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

async function RulesEmptyState({ canAdd }: { canAdd: boolean }) {
  const { t } = await getI18n();
  return (
    <EmptyState
      title={t("policies.version.emptyTitle")}
      description={
        canAdd
          ? t("policies.version.emptyBodyCanAdd")
          : t("policies.version.emptyBodyReadOnly")
      }
    />
  );
}
