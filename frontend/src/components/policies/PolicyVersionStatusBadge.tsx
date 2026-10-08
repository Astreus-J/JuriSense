import { FileClock, ShieldCheck } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { Badge } from "@/components/ui/Badge";
import type { BadgeTone } from "@/components/ui/Badge";
import { POLICY_VERSION_STATUS_LABELS } from "@/lib/policies/types";
import type { PolicyVersionStatus } from "@/lib/policies/types";

const STATUS_CONFIG: Record<PolicyVersionStatus, { tone: BadgeTone; icon: LucideIcon }> = {
  draft: { tone: "warning", icon: FileClock },
  published: { tone: "success", icon: ShieldCheck },
};

/**
 * `draft` renders as `warning` (not `neutral`) deliberately — a draft version's rules are
 * still mutable and it hasn't gone through the one-way publish freeze yet (BR-POL-001),
 * which is meaningfully different from a container-level `Policy.status` of "draft" (no
 * version at all exists yet). The distinct tone keeps that difference scannable at a
 * glance rather than color-identical to `PolicyStatusBadge`'s `draft`.
 */
export function PolicyVersionStatusBadge({ status }: { status: PolicyVersionStatus }) {
  const { tone, icon: Icon } = STATUS_CONFIG[status];
  return (
    <Badge tone={tone} icon={<Icon className="size-3.5" aria-hidden="true" />}>
      {POLICY_VERSION_STATUS_LABELS[status]}
    </Badge>
  );
}
