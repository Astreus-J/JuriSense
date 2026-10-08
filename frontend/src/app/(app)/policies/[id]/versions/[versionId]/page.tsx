import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft } from "lucide-react";

import { Alert } from "@/components/ui/Alert";
import { AddRuleControl } from "@/components/policies/AddRuleControl";
import { PolicyVersionStatusBadge } from "@/components/policies/PolicyVersionStatusBadge";
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
        <div className="space-y-6">
          <BackLink policyId={id} />
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
    <div className="space-y-8">
      <BackLink policyId={id} />

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-2xl font-semibold tracking-tight text-foreground">
              {policy.name} — Version {version.versionNumber}
            </h1>
            <PolicyVersionStatusBadge status={version.status} />
            {version.isCurrent && (
              <span className="text-xs font-medium text-foreground-muted">(current)</span>
            )}
          </div>
          <p className="mt-1 text-sm text-foreground-muted">
            {version.publishedAt
              ? `Published ${formatDateTime(version.publishedAt)}`
              : `Created ${formatDateTime(version.createdAt)}`}
          </p>
        </div>

        {isDraft && permissions.canUpdate && (
          <PublishVersionButton policyId={id} versionId={versionId} />
        )}
      </div>

      {!isDraft && (
        <Alert tone="info" title="This version is published and frozen">
          Every rule below is locked in permanently (BR-POL-001) — to change anything,
          create a new draft version from the policy page.
        </Alert>
      )}

      <div className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-foreground-muted">
            Rules
          </h2>
          {canAddRules && <AddRuleControl policyId={id} versionId={versionId} />}
        </div>

        {rules.length === 0 ? (
          <RulesEmptyState canAdd={canAddRules} />
        ) : (
          <ul className="space-y-3">
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
      </div>
    </div>
  );
}

function RulesEmptyState({ canAdd }: { canAdd: boolean }) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-xl border border-dashed border-border bg-surface px-6 py-12 text-center">
      <h3 className="text-sm font-semibold text-foreground">No rules yet</h3>
      <p className="max-w-sm text-sm text-foreground-muted">
        {canAdd
          ? "Add at least one rule before publishing — a version with no rules will never block or review anything."
          : "This version has no rules. Ask a policy author to add one before it's published."}
      </p>
    </div>
  );
}

function BackLink({ policyId }: { policyId: string }) {
  return (
    <Link
      href={`/policies/${policyId}`}
      className="inline-flex items-center gap-1 text-sm font-medium text-foreground-muted hover:text-foreground"
    >
      <ArrowLeft className="size-4" aria-hidden="true" />
      Back to policy
    </Link>
  );
}
