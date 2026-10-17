import { InvitationsList } from "@/components/organization/InvitationsList";
import { InviteUserForm } from "@/components/organization/InviteUserForm";
import { OrganizationPlanPanel } from "@/components/organization/OrganizationPlanPanel";
import { TeamTable } from "@/components/organization/TeamTable";
import { Alert } from "@/components/ui/Alert";
import { PageHeader } from "@/components/ui/PageHeader";
import { readAccessToken } from "@/lib/auth/cookies";
import { requireSession } from "@/lib/auth/session";
import { getI18n, pageTitle } from "@/lib/i18n/server";
import { ApiError, getMyOrganization, listInvites, listUsers } from "@/lib/organization/backend";
import { getOrganizationPermissions } from "@/lib/organization/permissions";

export const generateMetadata = pageTitle("meta.organizationSettings");

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
  const { t } = await getI18n();
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
      <PageHeader
        title={t("organization.title")}
        description={t("organization.description")}
      />

      {forbidden || !organization ? (
        <Alert tone="danger" title={t("organization.noAccessTitle")}>
          {t("organization.noAccessBody")}
        </Alert>
      ) : (
        <div className="space-y-8">
          <OrganizationPlanPanel organization={organization} />

          {permissions.canManageTeam ? (
            <>
              <section className="space-y-3">
                <div>
                  <h2 className="text-base font-semibold text-foreground">{t("organization.team.title")}</h2>
                  <p className="text-sm text-foreground-muted">
                    {t("organization.team.description")}
                  </p>
                </div>
                <TeamTable members={members} currentUserId={user.id} />
              </section>

              <section className="max-w-2xl space-y-3">
                <div>
                  <h2 className="text-base font-semibold text-foreground">{t("organization.invite.title")}</h2>
                  <p className="text-sm text-foreground-muted">
                    {t("organization.invite.description")}
                  </p>
                </div>
                <InviteUserForm />
              </section>

              <section className="space-y-3">
                <h2 className="text-base font-semibold text-foreground">{t("organization.invitations.title")}</h2>
                <InvitationsList invitations={invitations} />
              </section>
            </>
          ) : (
            <Alert tone="info" title={t("organization.readOnlyTitle")}>
              {t("organization.readOnlyBody")}
            </Alert>
          )}
        </div>
      )}
    </div>
  );
}
