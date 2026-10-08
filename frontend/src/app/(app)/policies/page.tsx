import type { Metadata } from "next";
import Link from "next/link";
import { Plus } from "lucide-react";

import { Alert } from "@/components/ui/Alert";
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
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">Policies</h1>
          <p className="mt-1 max-w-2xl text-sm text-foreground-muted">
            The rules that turn your organization&apos;s policy into an executable,
            versioned decision — every published version is frozen and reproducible, so
            past compliance decisions never silently change.
          </p>
        </div>
        {!forbidden && permissions.canCreate && (
          <Link href="/policies/new" className={buttonClasses("primary")}>
            <Plus className="size-4" aria-hidden="true" />
            Create policy
          </Link>
        )}
      </div>

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
  const Icon = NAV_ITEMS.policies.icon;
  return (
    <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-border bg-surface px-6 py-16 text-center">
      <div className="flex size-12 items-center justify-center rounded-full bg-surface-muted">
        <Icon className="size-6 text-foreground-muted" aria-hidden="true" />
      </div>
      <h2 className="text-lg font-semibold text-foreground">No policies yet</h2>
      <p className="max-w-sm text-sm text-foreground-muted">
        Create your first policy to start authoring the rules compliance reviews will
        evaluate contracts and suppliers against.
      </p>
      {canCreate && (
        <Link href="/policies/new" className={buttonClasses("primary", "mt-1")}>
          <Plus className="size-4" aria-hidden="true" />
          Create policy
        </Link>
      )}
    </div>
  );
}
