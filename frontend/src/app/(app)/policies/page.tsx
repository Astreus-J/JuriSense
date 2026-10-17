import type { Metadata } from "next";
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
import { NAV_ITEMS } from "@/lib/navigation/modules";
import { listPolicies } from "@/lib/policies/backend";
import { getPolicyPermissions } from "@/lib/policies/permissions";

export const metadata: Metadata = { title: "Policies — JuriSense Gate" };

export default async function PoliciesPage() {
  const user = await requireSession();
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
        title="Policies"
        description="The rules that turn your organization's policy into an executable, versioned decision. Every published version is frozen and reproducible, so past compliance decisions never silently change."
        actions={
          !forbidden && permissions.canCreate ? (
            <Link href="/policies/new" className={buttonClasses("primary")}>
              <Plus className="size-4" aria-hidden="true" />
              Create policy
            </Link>
          ) : undefined
        }
      />

      {forbidden ? (
        <Alert tone="danger" title="You don't have access to Policies.">
          Ask an administrator to grant you the &quot;policies&quot; read permission for
          this organization.
        </Alert>
      ) : policies.length === 0 ? (
        <PoliciesEmptyState canCreate={permissions.canCreate} />
      ) : (
        <PolicyTable policies={policies} />
      )}
    </div>
  );
}

function PoliciesEmptyState({ canCreate }: { canCreate: boolean }) {
  return (
    <EmptyState
      icon={NAV_ITEMS.policies.icon}
      title="No policies yet"
      description="Create your first policy to start authoring the rules compliance reviews will evaluate contracts and suppliers against."
      action={
        canCreate ? (
          <Link href="/policies/new" className={buttonClasses("primary")}>
            <Plus className="size-4" aria-hidden="true" />
            Create policy
          </Link>
        ) : undefined
      }
    />
  );
}
