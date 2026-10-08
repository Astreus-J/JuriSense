import { Archive, CheckCircle2, Clock } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { Badge } from "@/components/ui/Badge";
import type { BadgeTone } from "@/components/ui/Badge";
import { POLICY_STATUS_LABELS } from "@/lib/policies/types";
import type { PolicyStatus } from "@/lib/policies/types";

const STATUS_CONFIG: Record<PolicyStatus, { tone: BadgeTone; icon: LucideIcon }> = {
  draft: { tone: "neutral", icon: Clock },
  published: { tone: "success", icon: CheckCircle2 },
  archived: { tone: "neutral", icon: Archive },
};

/** A Server Component — the icon is rendered directly into markup, matching
 * `SupplierStatusBadge`'s exact pattern. */
export function PolicyStatusBadge({ status }: { status: PolicyStatus }) {
  const { tone, icon: Icon } = STATUS_CONFIG[status];
  return (
    <Badge tone={tone} icon={<Icon className="size-3.5" aria-hidden="true" />}>
      {POLICY_STATUS_LABELS[status]}
    </Badge>
  );
}
