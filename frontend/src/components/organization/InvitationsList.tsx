import { StatusBadge } from "@/components/shared/StatusBadge";
import { DataTable, Td, Th, Tr } from "@/components/ui/DataTable";
import { EmptyState } from "@/components/ui/EmptyState";
import { formatRoleLabel } from "@/lib/auth/types";
import type { Invitation } from "@/lib/organization/types";

interface InvitationsListProps {
  invitations: Invitation[];
}

/** Admin-only screen section, same gate as `TeamTable`. Explains what an empty state means
 * rather than a bare "No data" (persona: "Empty states should explain ... what the user
 * should do"). */
export function InvitationsList({ invitations }: InvitationsListProps) {
  if (invitations.length === 0) {
    return (
      <EmptyState
        title="No invitations sent yet"
        description="Invite a teammate using the form above. Pending and past invitations are listed here."
      />
    );
  }

  return (
    <DataTable caption="Invitations">
      <thead>
        <tr>
          <Th>Email</Th>
          <Th>Role</Th>
          <Th>Status</Th>
          <Th numeric>Expires</Th>
        </tr>
      </thead>
      <tbody>
        {invitations.map((invitation) => (
          <Tr key={invitation.id}>
            <Td className="font-medium text-foreground">{invitation.email}</Td>
            <Td muted className="whitespace-nowrap">
              {formatRoleLabel(invitation.role)}
            </Td>
            <Td>
              <StatusBadge kind="invitation" value={invitation.status} />
            </Td>
            <Td numeric muted className="whitespace-nowrap">
              {new Date(invitation.expiresAt).toLocaleDateString(undefined, {
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
