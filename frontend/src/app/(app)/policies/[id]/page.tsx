import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft } from "lucide-react";

import { Alert } from "@/components/ui/Alert";
import { CreateDraftVersionButton } from "@/components/policies/CreateDraftVersionButton";
import { PolicyStatusBadge } from "@/components/policies/PolicyStatusBadge";
import { PolicyVersionList } from "@/components/policies/PolicyVersionList";
import { ApiError } from "@/lib/auth/backend";
import { readAccessToken } from "@/lib/auth/cookies";
import { requireSession } from "@/lib/auth/session";
import { formatDateTime } from "@/lib/format";
import { getPolicy, listPolicyVersions } from "@/lib/policies/backend";
import { getPolicyPermissions } from "@/lib/policies/permissions";

export const metadata: Metadata = { title: "Policy — JuriSense Gate" };

interface PolicyDetailPageProps {
  // Next 16: `params` is a Promise (see `node_modules/next/dist/docs/01-app/
  // 03-api-reference/03-file-conventions/page.md`).
  params: Promise<{ id: string }>;
}

export default async function PolicyDetailPage({ params }: PolicyDetailPageProps) {
  const user = await requireSession();
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
        <div className="space-y-6">
          <BackLink />
          <Alert tone="danger" title="You don't have access to this policy.">
            Ask an administrator to grant you the &quot;policies&quot; read permission for
            this organization.
          </Alert>
        </div>
      );
    }
    throw error;
  }

  const versions = await listPolicyVersions(accessToken, id);

  return (
    <div className="space-y-8">
      <BackLink />

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-2xl font-semibold tracking-tight text-foreground">{policy.name}</h1>
            <PolicyStatusBadge status={policy.status} />
          </div>
          <p className="mt-1 text-sm text-foreground-muted">
            Created {formatDateTime(policy.createdAt)}
          </p>
        </div>

        {permissions.canCreate && <CreateDraftVersionButton policyId={policy.id} />}
      </div>

      <div className="space-y-3">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-foreground-muted">
          Versions
        </h2>
        {versions.length === 0 ? (
          // A Policy is only ever created together with its first draft version
          // (`policy_service.create_policy`) — this is a defensive branch for an
          // invariant that should never actually break, not an expected empty state.
          <Alert tone="warning" title="This policy has no versions yet.">
            This shouldn&apos;t normally happen — contact support if it persists.
          </Alert>
        ) : (
          <PolicyVersionList policyId={policy.id} versions={versions} />
        )}
      </div>
    </div>
  );
}

function BackLink() {
  return (
    <Link
      href="/policies"
      className="inline-flex items-center gap-1 text-sm font-medium text-foreground-muted hover:text-foreground"
    >
      <ArrowLeft className="size-4" aria-hidden="true" />
      Back to policies
    </Link>
  );
}
