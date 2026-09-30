import { AlertTriangle, CheckCircle2, Loader2, XCircle } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { Badge } from "@/components/ui/Badge";
import type { BadgeTone } from "@/components/ui/Badge";
import { CONTRACT_VERSION_STATUS_LABELS } from "@/lib/contracts/types";
import type { ContractVersionStatus } from "@/lib/contracts/types";

const STATUS_CONFIG: Record<ContractVersionStatus, { tone: BadgeTone; icon: LucideIcon }> = {
  extracted: { tone: "neutral", icon: Loader2 },
  needs_confirmation: { tone: "warning", icon: AlertTriangle },
  analyzed: { tone: "success", icon: CheckCircle2 },
  extraction_failed: { tone: "danger", icon: XCircle },
};

/** A `ContractVersion`'s AI-extraction/analysis status — see the status enum's docstring
 * in `lib/contracts/types.ts` for what each value actually means (`extracted` is a
 * transient "processing" state, not "extraction complete"). */
export function ContractVersionStatusBadge({ status }: { status: ContractVersionStatus }) {
  const { tone, icon: Icon } = STATUS_CONFIG[status];
  return (
    <Badge
      tone={tone}
      icon={
        <Icon
          className={status === "extracted" ? "size-3.5 motion-safe:animate-spin" : "size-3.5"}
          aria-hidden="true"
        />
      }
    >
      {CONTRACT_VERSION_STATUS_LABELS[status]}
    </Badge>
  );
}
