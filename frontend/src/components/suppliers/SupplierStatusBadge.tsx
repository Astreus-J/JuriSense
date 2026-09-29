import { Archive, Ban, CheckCircle2, Clock, Search } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { Badge } from "@/components/ui/Badge";
import type { BadgeTone } from "@/components/ui/Badge";
import { SUPPLIER_STATUS_LABELS } from "@/lib/suppliers/types";
import type { SupplierStatus } from "@/lib/suppliers/types";

const STATUS_CONFIG: Record<SupplierStatus, { tone: BadgeTone; icon: LucideIcon }> = {
  prospect: { tone: "neutral", icon: Clock },
  under_review: { tone: "info", icon: Search },
  approved: { tone: "success", icon: CheckCircle2 },
  blocked: { tone: "danger", icon: Ban },
  inactive: { tone: "neutral", icon: Archive },
};

/**
 * A Server Component — the icon is rendered here, directly into markup, never passed as a
 * prop into a Client Component (see `SidebarContent.tsx`'s note on why a raw icon reference
 * can't cross the Server->Client boundary; this file never crosses it in the first place).
 */
export function SupplierStatusBadge({ status }: { status: SupplierStatus }) {
  const { tone, icon: Icon } = STATUS_CONFIG[status];
  return (
    <Badge tone={tone} icon={<Icon className="size-3.5" aria-hidden="true" />}>
      {SUPPLIER_STATUS_LABELS[status]}
    </Badge>
  );
}
