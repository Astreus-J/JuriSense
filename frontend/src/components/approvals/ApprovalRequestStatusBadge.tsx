import { CheckCircle2, Clock, XCircle } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { Badge } from "@/components/ui/Badge";
import type { BadgeTone } from "@/components/ui/Badge";
import { APPROVAL_REQUEST_STATUS_LABELS } from "@/lib/approvals/types";
import type { ApprovalRequestStatus } from "@/lib/approvals/types";

const STATUS_CONFIG: Record<ApprovalRequestStatus, { tone: BadgeTone; icon: LucideIcon }> = {
  pending: { tone: "warning", icon: Clock },
  approved: { tone: "success", icon: CheckCircle2 },
  rejected: { tone: "danger", icon: XCircle },
};

/** An `ApprovalRequest.status` pill — mirrors `ComplianceStatusBadge`'s shape. Every item
 * `/approvals` lists is `pending` by construction (its only data source is `GET /approvals/
 * requests/pending`), but the component models all three states for when a resolved
 * request is shown elsewhere (e.g. a future per-review Approvals sub-view). */
export function ApprovalRequestStatusBadge({ status }: { status: ApprovalRequestStatus }) {
  const { tone, icon: Icon } = STATUS_CONFIG[status];
  return (
    <Badge tone={tone} icon={<Icon className="size-3.5" aria-hidden="true" />}>
      {APPROVAL_REQUEST_STATUS_LABELS[status]}
    </Badge>
  );
}
