import { Ban, CheckCircle2, Clock, XCircle } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { Badge } from "@/components/ui/Badge";
import type { BadgeTone } from "@/components/ui/Badge";
import { formatRoleLabel } from "@/lib/auth/types";
import { INVITATION_STATUS_LABELS } from "@/lib/organization/types";
import type { Invitation, InvitationStatus } from "@/lib/organization/types";

interface InvitationsListProps {
  invitations: Invitation[];
}

const STATUS_CONFIG: Record<InvitationStatus, { tone: BadgeTone; icon: LucideIcon }> = {
  pending: { tone: "info", icon: Clock },
  accepted: { tone: "success", icon: CheckCircle2 },
  expired: { tone: "neutral", icon: Ban },
  cancelled: { tone: "danger", icon: XCircle },
};

/** Admin-only screen section, same gate as `TeamTable`. Explains what an empty state means
 * rather than a bare "No data" (persona: "Empty states should explain ... what the user
 * should do"). */
export function InvitationsList({ invitations }: InvitationsListProps) {
  if (invitations.length === 0) {
    return (
      <p className="rounded-lg border border-dashed border-border bg-surface px-4 py-6 text-center text-sm text-foreground-muted">
        No invitations sent yet. Invite a teammate using the form above.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-border bg-surface">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-border bg-surface-muted text-xs uppercase tracking-wide text-foreground-muted">
          <tr>
            <th className="px-4 py-3 font-medium">Email</th>
            <th className="px-4 py-3 font-medium">Role</th>
            <th className="px-4 py-3 font-medium">Status</th>
            <th className="px-4 py-3 font-medium">Expires</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {invitations.map((invitation) => {
            const { tone, icon: Icon } = STATUS_CONFIG[invitation.status];
            return (
              <tr key={invitation.id} className="hover:bg-surface-muted">
                <td className="px-4 py-3 font-medium text-foreground">{invitation.email}</td>
                <td className="px-4 py-3 text-foreground-muted">
                  {formatRoleLabel(invitation.role)}
                </td>
                <td className="px-4 py-3">
                  <Badge tone={tone} icon={<Icon className="size-3.5" aria-hidden="true" />}>
                    {INVITATION_STATUS_LABELS[invitation.status]}
                  </Badge>
                </td>
                <td className="px-4 py-3 text-foreground-muted">
                  {new Date(invitation.expiresAt).toLocaleDateString(undefined, {
                    year: "numeric",
                    month: "short",
                    day: "numeric",
                  })}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
