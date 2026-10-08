import type { Metadata } from "next";

import { Alert } from "@/components/ui/Alert";
import { ApprovalRequestRow } from "@/components/approvals/ApprovalRequestRow";
import { ApiError, listPendingApprovalRequests } from "@/lib/approvals/backend";
import { getApprovalPermissions } from "@/lib/approvals/permissions";
import { readAccessToken } from "@/lib/auth/cookies";
import { requireSession } from "@/lib/auth/session";
import { NAV_ITEMS } from "@/lib/navigation/modules";

export const metadata: Metadata = { title: "Approvals — JuriSense Gate" };

/**
 * The Approvals inbox: every pending `ApprovalRequest` routed to the caller's own role,
 * across every `ComplianceReview` (`GET /approvals/requests/pending`). Follows `(app)/
 * suppliers/page.tsx`'s exact Server Component pattern: `requireSession()`, read the
 * access token, fetch, and degrade a 403 into an `Alert` instead of letting it throw.
 */
export default async function ApprovalsPage() {
  const user = await requireSession();
  const permissions = getApprovalPermissions(user.role);

  const accessToken = await readAccessToken();
  let approvalRequests: Awaited<ReturnType<typeof listPendingApprovalRequests>> = [];
  let forbidden = false;

  try {
    // `requireSession()` above already guarantees a valid token exists; the `!` mirrors
    // the same non-null assumption `getSession()` makes right after its own read.
    approvalRequests = await listPendingApprovalRequests(accessToken!);
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
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Approvals</h1>
        <p className="mt-1 max-w-2xl text-sm text-foreground-muted">
          Approval requests routed to your role, with a link to the compliance review and
          evidence behind each one.
        </p>
      </div>

      {forbidden ? (
        <Alert tone="danger" title="You don't have access to Approvals.">
          Ask an administrator to grant you the &quot;approvals&quot; read permission for
          this organization.
        </Alert>
      ) : approvalRequests.length === 0 ? (
        <ApprovalsEmptyState />
      ) : (
        <ul className="space-y-3">
          {approvalRequests.map((approvalRequest) => (
            <ApprovalRequestRow
              key={approvalRequest.id}
              request={approvalRequest}
              canUpdate={permissions.canUpdate}
            />
          ))}
        </ul>
      )}
    </div>
  );
}

function ApprovalsEmptyState() {
  const Icon = NAV_ITEMS.approvals.icon;
  return (
    <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-border bg-surface px-6 py-16 text-center">
      <div className="flex size-12 items-center justify-center rounded-full bg-surface-muted">
        <Icon className="size-6 text-foreground-muted" aria-hidden="true" />
      </div>
      <h2 className="text-lg font-semibold text-foreground">Your inbox is empty</h2>
      <p className="max-w-sm text-sm text-foreground-muted">
        No approval requests are currently routed to your role. New requests appear here as
        soon as a compliance review triggers a rule that needs your sign-off.
      </p>
    </div>
  );
}
