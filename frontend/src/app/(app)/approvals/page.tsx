import { Alert } from "@/components/ui/Alert";
import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { ApprovalRequestRow } from "@/components/approvals/ApprovalRequestRow";
import { ApiError, listPendingApprovalRequests } from "@/lib/approvals/backend";
import { getApprovalPermissions } from "@/lib/approvals/permissions";
import { readAccessToken } from "@/lib/auth/cookies";
import { requireSession } from "@/lib/auth/session";
import { getI18n, pageTitle } from "@/lib/i18n/server";
import { NAV_ITEMS } from "@/lib/navigation/modules";

export const generateMetadata = pageTitle("meta.approvals");

/**
 * The Approvals inbox: every pending `ApprovalRequest` routed to the caller's own role,
 * across every `ComplianceReview` (`GET /approvals/requests/pending`). Follows `(app)/
 * suppliers/page.tsx`'s exact Server Component pattern: `requireSession()`, read the
 * access token, fetch, and degrade a 403 into an `Alert` instead of letting it throw.
 */
export default async function ApprovalsPage() {
  const user = await requireSession();
  const { t, plural } = await getI18n();
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
    <div className="space-y-5">
      <PageHeader
        title={t("nav.approvals")}
        description={t("approvals.description")}
        meta={
          !forbidden && approvalRequests.length > 0 ? (
            <span className="text-sm text-foreground-muted">
              <span className="font-medium tabular-nums text-foreground">{approvalRequests.length}</span>{" "}
              {plural("approvals.pendingCount", approvalRequests.length)}
            </span>
          ) : undefined
        }
      />

      {forbidden ? (
        <Alert tone="danger" title={t("approvals.forbiddenTitle")}>
          {t("approvals.forbiddenBody")}
        </Alert>
      ) : approvalRequests.length === 0 ? (
        <EmptyState
          icon={NAV_ITEMS.approvals.icon}
          title={t("approvals.emptyTitle")}
          description={t("approvals.emptyBody")}
        />
      ) : (
        <ul className="divide-y divide-border border-y border-border">
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
