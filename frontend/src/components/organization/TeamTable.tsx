import { Ban, CheckCircle2, Clock, XCircle } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { Badge } from "@/components/ui/Badge";
import type { BadgeTone } from "@/components/ui/Badge";
import { formatRoleLabel } from "@/lib/auth/types";
import { USER_STATUS_LABELS } from "@/lib/organization/types";
import type { TeamMember, UserStatus } from "@/lib/organization/types";
import { TeamMemberActions } from "./TeamMemberActions";

interface TeamTableProps {
  members: TeamMember[];
  /** The id of the admin viewing this table — passed down to `TeamMemberActions` so it can
   * disable self-targeting actions the backend rejects anyway (see that component). */
  currentUserId: string;
}

const STATUS_CONFIG: Record<UserStatus, { tone: BadgeTone; icon: LucideIcon }> = {
  active: { tone: "success", icon: CheckCircle2 },
  pending: { tone: "info", icon: Clock },
  inactive: { tone: "neutral", icon: Ban },
  blocked: { tone: "danger", icon: XCircle },
};

/** Admin-only screen section — `OrganizationSettingsPage` only renders this when
 * `getOrganizationPermissions(role).canManageTeam` is true. */
export function TeamTable({ members, currentUserId }: TeamTableProps) {
  return (
    <div className="overflow-x-auto rounded-xl border border-border bg-surface">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-border bg-surface-muted text-xs uppercase tracking-wide text-foreground-muted">
          <tr>
            <th className="px-4 py-3 font-medium">Name</th>
            <th className="px-4 py-3 font-medium">Email</th>
            <th className="px-4 py-3 font-medium">Role</th>
            <th className="px-4 py-3 font-medium">Status</th>
            <th className="px-4 py-3 font-medium text-right">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {members.map((member) => {
            const { tone, icon: Icon } = STATUS_CONFIG[member.status];
            return (
              <tr key={member.id} className="hover:bg-surface-muted">
                <td className="px-4 py-3 font-medium text-foreground">{member.fullName}</td>
                <td className="px-4 py-3 text-foreground-muted">{member.email}</td>
                <td className="px-4 py-3 text-foreground-muted">
                  {formatRoleLabel(member.role)}
                </td>
                <td className="px-4 py-3">
                  <Badge tone={tone} icon={<Icon className="size-3.5" aria-hidden="true" />}>
                    {USER_STATUS_LABELS[member.status]}
                  </Badge>
                </td>
                <td className="px-4 py-3 text-right">
                  <TeamMemberActions member={member} isSelf={member.id === currentUserId} />
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
