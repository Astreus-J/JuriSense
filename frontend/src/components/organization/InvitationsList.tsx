import { StatusBadge } from "@/components/shared/StatusBadge";
import { DataTable, Td, Th, Tr } from "@/components/ui/DataTable";
import { EmptyState } from "@/components/ui/EmptyState";
import { INTL_LOCALES } from "@/lib/i18n/config";
import { getI18n } from "@/lib/i18n/server";
import type { Invitation } from "@/lib/organization/types";

interface InvitationsListProps {
  invitations: Invitation[];
}

/** Admin-only screen section, same gate as `TeamTable`. Explains what an empty state means
 * rather than a bare "No data" (persona: "Empty states should explain ... what the user
 * should do"). */
export async function InvitationsList({ invitations }: InvitationsListProps) {
  const { t, locale } = await getI18n();
  if (invitations.length === 0) {
    return (
      <EmptyState
        title={t("organization.invitations.emptyTitle")}
        description={t("organization.invitations.emptyBody")}
      />
    );
  }

  return (
    <DataTable caption={t("organization.invitations.caption")}>
      <thead>
        <tr>
          <Th>{t("organization.invitations.email")}</Th>
          <Th>{t("organization.invitations.role")}</Th>
          <Th>{t("organization.invitations.status")}</Th>
          <Th numeric>{t("organization.invitations.expires")}</Th>
        </tr>
      </thead>
      <tbody>
        {invitations.map((invitation) => (
          <Tr key={invitation.id}>
            <Td className="font-medium text-foreground">{invitation.email}</Td>
            <Td muted className="whitespace-nowrap">
              {t(`role.${invitation.role}`)}
            </Td>
            <Td>
              <StatusBadge kind="invitation" value={invitation.status} />
            </Td>
            <Td numeric muted className="whitespace-nowrap">
              {new Date(invitation.expiresAt).toLocaleDateString(INTL_LOCALES[locale], {
                year: "numeric",
                month: "short",
                day: "numeric",
              })}
            </Td>
          </Tr>
        ))}
      </tbody>
    </DataTable>
  );
}
