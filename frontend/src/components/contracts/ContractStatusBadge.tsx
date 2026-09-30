import { Archive, Ban, CheckCircle2, FileEdit, RefreshCw, Search } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { Badge } from "@/components/ui/Badge";
import type { BadgeTone } from "@/components/ui/Badge";
import { CONTRACT_STATUS_LABELS } from "@/lib/contracts/types";
import type { ContractStatus } from "@/lib/contracts/types";

const STATUS_CONFIG: Record<ContractStatus, { tone: BadgeTone; icon: LucideIcon }> = {
  draft: { tone: "neutral", icon: FileEdit },
  under_review: { tone: "info", icon: Search },
  active: { tone: "success", icon: CheckCircle2 },
  renewed: { tone: "info", icon: RefreshCw },
  terminated: { tone: "danger", icon: Ban },
  expired: { tone: "neutral", icon: Archive },
};

/** The `Contract`'s own commercial/legal status — distinct from any one
 * `ContractVersion`'s extraction status (`ContractVersionStatusBadge`). */
export function ContractStatusBadge({ status }: { status: ContractStatus }) {
  const { tone, icon: Icon } = STATUS_CONFIG[status];
  return (
    <Badge tone={tone} icon={<Icon className="size-3.5" aria-hidden="true" />}>
      {CONTRACT_STATUS_LABELS[status]}
    </Badge>
  );
}
