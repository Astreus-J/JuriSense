import { StatusBadge } from "@/components/shared/StatusBadge";
import { DataTable, Td, Th, Tr } from "@/components/ui/DataTable";
import { getI18n } from "@/lib/i18n/server";
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
export async function TeamTable({ members, currentUserId }: TeamTableProps) {
  const { t } = await getI18n();
  return (
    <DataTable caption={t("organization.team.caption")}>
      <thead>
        <tr>
          <Th>{t("organization.team.name")}</Th>
          <Th>{t("organization.team.email")}</Th>
          <Th>{t("organization.team.role")}</Th>
          <Th>{t("organization.team.status")}</Th>
          <Th numeric>{t("organization.team.actions")}</Th>
        </tr>
      </thead>
      <tbody>
        {members.map((member) => (
          <Tr key={member.id}>
            <Td className="font-medium text-foreground">{member.fullName}</Td>
            <Td muted>{member.email}</Td>
            <Td muted className="whitespace-nowrap">
              {t(`role.${member.role}`)}
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
