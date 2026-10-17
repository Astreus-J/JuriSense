import { redirect } from "next/navigation";

import { AcceptInviteForm } from "@/components/auth/AcceptInviteForm";
import { AuthShell } from "@/components/auth/AuthShell";
import { Alert } from "@/components/ui/Alert";
import { getSession } from "@/lib/auth/session";
import { getI18n } from "@/lib/i18n/server";
import { PRODUCT_NAME } from "@/lib/i18n/config";

export async function generateMetadata() {
  const { t } = await getI18n();
  return {
    title: `${t("meta.acceptInvite")} — ${PRODUCT_NAME}`,
    description: t("meta.acceptInviteDescription"),
  };
}

interface AcceptInvitePageProps {
  searchParams: Promise<{ token?: string }>;
}

export default async function AcceptInvitePage({ searchParams }: AcceptInvitePageProps) {
  const { token } = await searchParams;
  const { t } = await getI18n();

  const session = await getSession();
  if (session) redirect("/dashboard");

  if (!token) {
    return (
      <AuthShell heading={t("auth.invite.missingHeading")}>
        <Alert tone="danger" title={t("auth.invite.missingTitle")}>
          {t("auth.invite.missingBody")}
        </Alert>
      </AuthShell>
    );
  }

  return (
    <AuthShell
      heading={t("auth.invite.heading")}
      subtext={t("auth.invite.subtext")}
    >
      <AcceptInviteForm token={token} />
    </AuthShell>
  );
}
