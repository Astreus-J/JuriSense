import { CheckCircle2, Loader2, XCircle } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { Badge } from "@/components/ui/Badge";
import type { BadgeTone } from "@/components/ui/Badge";
import { SUPPLIER_CHECK_STATUS_LABELS } from "@/lib/suppliers/types";
import type { SupplierCheckStatus } from "@/lib/suppliers/types";

const STATUS_CONFIG: Record<
  SupplierCheckStatus,
  { tone: BadgeTone; icon: LucideIcon; spin?: boolean }
> = {
  started: { tone: "info", icon: Loader2, spin: true },
  completed: { tone: "success", icon: CheckCircle2 },
  failed: { tone: "danger", icon: XCircle },
};

export function SupplierCheckStatusBadge({ status }: { status: SupplierCheckStatus }) {
  const { tone, icon: Icon, spin } = STATUS_CONFIG[status];
  return (
    <Badge
      tone={tone}
      icon={<Icon className={spin ? "size-3.5 motion-safe:animate-spin" : "size-3.5"} aria-hidden="true" />}
    >
      {SUPPLIER_CHECK_STATUS_LABELS[status]}
    </Badge>
  );
}
