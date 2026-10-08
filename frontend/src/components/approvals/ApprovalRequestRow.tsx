import Link from "next/link";
import { ArrowRight } from "lucide-react";

import { Badge } from "@/components/ui/Badge";
import { formatRoleLabel, isRole } from "@/lib/auth/types";
import { formatDateTime } from "@/lib/format";
import type { ApprovalRequest } from "@/lib/approvals/types";
import { ApprovalActions } from "./ApprovalActions";
import { ApprovalRequestStatusBadge } from "./ApprovalRequestStatusBadge";

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
 * `canUpdate` is a UI-only hint (`getApprovalPermissions`) — a read-only-role viewer still
 * sees the full request (role, step, timing, link to evidence), just without the
 * Approve/Reject controls.
 */
export function ApprovalRequestRow({ request, canUpdate }: ApprovalRequestRowProps) {
  const roleLabel = isRole(request.approverRole)
    ? formatRoleLabel(request.approverRole)
    : request.approverRole;

  return (
    <li className="space-y-3 rounded-xl border border-border bg-surface p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone="neutral">
            Step {request.stepNumber} · {roleLabel}
          </Badge>
          <ApprovalRequestStatusBadge status={request.status} />
        </div>
        <span className="text-xs text-foreground-muted">
          Requested {formatDateTime(request.requestedAt)}
        </span>
      </div>

      <Link
        href={`/compliance/reviews/${request.complianceReviewId}`}
        className="inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline"
      >
        View compliance review
        <ArrowRight className="size-3.5" aria-hidden="true" />
      </Link>

      {canUpdate && <ApprovalActions requestId={request.id} />}
    </li>
  );
}
