import { StatusBadge } from "@/components/shared/StatusBadge";
import { DataTable, Td, Th, Tr } from "@/components/ui/DataTable";
import { formatRoleLabel } from "@/lib/auth/types";
import type { TeamMember } from "@/lib/organization/types";
import { TeamMemberActions } from "./TeamMemberActions";

interface TeamTableProps {
  members: TeamMember[];
  /** The id of the admin viewing this table — passed down to `TeamMemberActions` so it can
   * disable self-targeting actions the backend rejects anyway (see that component). */
  currentUserId: string;
}

/** Admin-only screen section — `OrganizationSettingsPage` only renders this when
 * `getOrganizationPermissions(role).canManageTeam` is true. */
export function TeamTable({ members, currentUserId }: TeamTableProps) {
  return (
    <DataTable caption="Team members">
      <thead>
        <tr>
          <Th>Name</Th>
          <Th>Email</Th>
          <Th>Role</Th>
          <Th>Status</Th>
          <Th numeric>Actions</Th>
        </tr>
      </thead>
      <tbody>
        {members.map((member) => (
          <Tr key={member.id}>
            <Td className="font-medium text-foreground">{member.fullName}</Td>
            <Td muted>{member.email}</Td>
            <Td muted className="whitespace-nowrap">
              {formatRoleLabel(member.role)}
            </Td>
            <Td>
              <StatusBadge kind="user" value={member.status} />
            </Td>
            <Td className="text-right">
              <TeamMemberActions member={member} isSelf={member.id === currentUserId} />
            </Td>
          </Tr>
        ))}
      </tbody>
    </DataTable>
  );
}
