import Link from "next/link";
import { ArrowRight } from "lucide-react";

import { StatusBadge } from "@/components/shared/StatusBadge";
import { isRole } from "@/lib/auth/types";
import { formatDateTime } from "@/lib/format";
import { getI18n } from "@/lib/i18n/server";
import type { ApprovalRequest } from "@/lib/approvals/types";
import { ApprovalActions } from "./ApprovalActions";

interface ApprovalRequestRowProps {
  request: ApprovalRequest;
  canUpdate: boolean;
}

/**
 * One pending `ApprovalRequest` in the inbox. `ApprovalRequestResponse` carries no
 * supplier/contract/review name — per this screen's brief, the row links out to the
 * existing, already-built `/compliance/reviews/{id}` results screen
 * (`ComplianceReviewResults`) for the WHY/EVIDENCE/POLICY/SOURCE behind it, rather than
 * re-fetching or re-rendering any rule evaluations here.
 *
 * Layout: what is being asked (step + role, when, link to the evidence) on the left, the
 * decision controls on the right from `md` up, stacked on narrow screens. A divided list row
 * rather than a card: the inbox is a queue to work through, so rows must scan quickly.
 *
 * `canUpdate` is a UI-only hint (`getApprovalPermissions`) — a read-only-role viewer still
 * sees the full request (role, step, timing, link to evidence), just without the
 * Approve/Reject controls.
 */
export async function ApprovalRequestRow({ request, canUpdate }: ApprovalRequestRowProps) {
  const { t, locale } = await getI18n();
  const roleLabel = isRole(request.approverRole)
    ? t(`role.${request.approverRole}`)
    : request.approverRole;

  return (
    <li className="grid gap-4 py-4 md:grid-cols-[minmax(0,1fr)_minmax(0,22rem)] md:gap-8">
      <div className="space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="text-sm font-semibold text-foreground">
            {t("approvals.row.step", { number: request.stepNumber })}
          </h2>
          <StatusBadge kind="approvalRequest" value={request.status} />
        </div>
        <dl className="space-y-0.5 text-sm">
          <div className="flex gap-2">
            <dt className="w-20 shrink-0 text-foreground-muted">{t("approvals.row.approver")}</dt>
            <dd>{roleLabel}</dd>
          </div>
          <div className="flex gap-2">
            <dt className="w-20 shrink-0 text-foreground-muted">{t("approvals.row.requested")}</dt>
            <dd className="tabular-nums">{formatDateTime(request.requestedAt, locale)}</dd>
          </div>
        </dl>
        <Link
          href={`/compliance/reviews/${request.complianceReviewId}`}
          className="inline-flex items-center gap-1 rounded text-sm font-medium text-primary hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring"
        >
          {t("approvals.row.viewReview")}
          <ArrowRight className="size-3.5" aria-hidden="true" />
        </Link>
      </div>

      {canUpdate && <ApprovalActions requestId={request.id} />}
    </li>
  );
}
