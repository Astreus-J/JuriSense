import type { Metadata } from "next";

import { InvitationsList } from "@/components/organization/InvitationsList";
import { InviteUserForm } from "@/components/organization/InviteUserForm";
import { OrganizationPlanPanel } from "@/components/organization/OrganizationPlanPanel";
import { TeamTable } from "@/components/organization/TeamTable";
import { Alert } from "@/components/ui/Alert";
import { readAccessToken } from "@/lib/auth/cookies";
import { requireSession } from "@/lib/auth/session";
import { ApiError, getMyOrganization, listInvites, listUsers } from "@/lib/organization/backend";
import { getOrganizationPermissions } from "@/lib/organization/permissions";

export const metadata: Metadata = { title: "Organization — JuriSense Gate" };

/**
 * The "Settings" module's one real screen today: the organization's plan/usage panel plus
 * team management. Two independent gates, both enforced for real server-side and only
 * *hinted* at here (persona: "Backend authorization remains authoritative"):
 *
 * - Reading the plan/usage panel at all (`GET /organizations/me`) is gated on the real
 *   `organization_settings` RBAC permission — `admin`, `security`, and `auditor` by default.
 *   A 403 here is a normal, handled state (like `SuppliersPage`'s), not a crash.
 * - Managing the team (role changes, deactivation, invites) is hardcoded admin-only
 *   server-side regardless of the RBAC grid, so a `security`/`auditor` viewer who can read
 *   the panel still only ever sees it — the team section is omitted entirely rather than
 *   shown with disabled controls.
 */
export default async function OrganizationSettingsPage() {
  const user = await requireSession();
  const permissions = getOrganizationPermissions(user.role);
  // `requireSession()` above already guarantees a valid token exists; the `!` below mirrors
  // the same non-null assumption `getSession()` makes right after its own read.
  const accessToken = await readAccessToken();

  let organization: Awaited<ReturnType<typeof getMyOrganization>> | null = null;
  let forbidden = false;

  try {
    organization = await getMyOrganization(accessToken!);
  } catch (error) {
    if (error instanceof ApiError && error.status === 403) {
      forbidden = true;
    } else {
      // Anything else (5xx, network) is a real failure — let the segment's error.tsx handle it.
      throw error;
    }
  }

  let members: Awaited<ReturnType<typeof listUsers>> = [];
  let invitations: Awaited<ReturnType<typeof listInvites>> = [];
  if (!forbidden && permissions.canManageTeam) {
    [members, invitations] = await Promise.all([
      listUsers(accessToken!),
      listInvites(accessToken!),
    ]);
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Organization</h1>
        <p className="mt-1 max-w-2xl text-sm text-foreground-muted">
          Your organization&apos;s plan, usage, and team.
        </p>
      </div>

      {forbidden || !organization ? (
        <Alert tone="danger" title="You don't have access to organization settings.">
          Ask an administrator to grant you the &quot;organization settings&quot; read
          permission for this organization.
        </Alert>
      ) : (
        <div className="space-y-8">
          <OrganizationPlanPanel organization={organization} />

          {permissions.canManageTeam ? (
            <>
              <section className="space-y-4">
                <div>
                  <h2 className="text-lg font-semibold text-foreground">Team</h2>
                  <p className="mt-1 text-sm text-foreground-muted">
                    Everyone with access to this organization, and their role.
                  </p>
                </div>
                <TeamTable members={members} currentUserId={user.id} />
              </section>

              <section className="space-y-4">
                <div>
                  <h2 className="text-lg font-semibold text-foreground">Invite someone</h2>
                  <p className="mt-1 text-sm text-foreground-muted">
                    They&apos;ll receive an email with a link to set their own password.
                  </p>
                </div>
                <InviteUserForm />
              </section>

              <section className="space-y-4">
                <h2 className="text-lg font-semibold text-foreground">Pending invitations</h2>
                <InvitationsList invitations={invitations} />
              </section>
            </>
          ) : (
            <Alert tone="info" title="Read-only access">
              You can view your organization&apos;s plan and usage. Team management is
              restricted to administrators.
            </Alert>
          )}
        </div>
      )}
    </div>
  );
}
