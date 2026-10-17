import { StatusBadge } from "@/components/shared/StatusBadge";
import type { Metadata } from "next";
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
import { getPolicy, getPolicyVersion, listRules } from "@/lib/policies/backend";
import { getPolicyPermissions } from "@/lib/policies/permissions";

export const metadata: Metadata = { title: "Policy version — JuriSense Gate" };

interface PolicyVersionDetailPageProps {
  // Next 16: `params` is a Promise.
  params: Promise<{ id: string; versionId: string }>;
}

export default async function PolicyVersionDetailPage({ params }: PolicyVersionDetailPageProps) {
  const user = await requireSession();
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
          <PageHeader title="Policy version" breadcrumbs={[{ label: "Policies", href: "/policies" }, { label: "Policy", href: `/policies/${id}` }, { label: "Version" }]} />
          <Alert tone="danger" title="You don't have access to this policy version.">
            Ask an administrator to grant you the &quot;policies&quot; read permission for
            this organization.
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
          { label: "Policies", href: "/policies" },
          { label: policy.name, href: `/policies/${id}` },
          { label: `Version ${version.versionNumber}` },
        ]}
        title={`${policy.name}, version ${version.versionNumber}`}
        meta={
          <>
            <StatusBadge kind="policyVersion" value={version.status} />
            {version.isCurrent && <span className="text-xs text-foreground-muted">current</span>}
            <span className="text-sm tabular-nums text-foreground-muted">
              {version.publishedAt
                ? `Published ${formatDateTime(version.publishedAt)}`
                : `Created ${formatDateTime(version.createdAt)}`}
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
        <Alert tone="info" title="This version is published and frozen">
          Every rule below is locked in permanently (BR-POL-001) — to change anything,
          create a new draft version from the policy page.
        </Alert>
      )}

      <section className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <h2 className="text-base font-semibold text-foreground">
            Rules <span className="font-normal tabular-nums text-foreground-muted">({rules.length})</span>
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

function RulesEmptyState({ canAdd }: { canAdd: boolean }) {
  return (
    <EmptyState
      title="No rules yet"
      description={
        canAdd
          ? "Add at least one rule before publishing. A version with no rules will never block or review anything."
          : "This version has no rules. Ask a policy author to add one before it's published."
      }
    />
  );
}
