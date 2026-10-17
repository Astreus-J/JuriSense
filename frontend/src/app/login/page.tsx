import { redirect } from "next/navigation";

import { AuthShell } from "@/components/auth/AuthShell";
import { LoginForm } from "@/components/auth/LoginForm";
import { Alert } from "@/components/ui/Alert";
import { isSafeNextPath } from "@/lib/auth/safe-redirect";
import { getSession } from "@/lib/auth/session";
import { getI18n } from "@/lib/i18n/server";
import { PRODUCT_NAME } from "@/lib/i18n/config";

export async function generateMetadata() {
  const { t } = await getI18n();
  return { title: `${t("meta.signIn")} — ${PRODUCT_NAME}`, description: t("meta.signInDescription") };
}

interface LoginPageProps {
  searchParams: Promise<{ next?: string; expired?: string; accountCreated?: string }>;
}

export default async function LoginPage({ searchParams }: LoginPageProps) {
  const { t } = await getI18n();
  const { next, expired, accountCreated } = await searchParams;
  const safeNext = isSafeNextPath(next) ? next : "/dashboard";

  // Already signed in: no reason to show the login form again.
  const session = await getSession();
  if (session) redirect(safeNext);

  return (
    <AuthShell
      heading={t("auth.signIn.heading")}
      subtext={t("auth.signIn.subtext")}
    >
      <div className="space-y-5">
        {expired === "1" && (
          <Alert tone="warning" title={t("auth.signIn.sessionExpiredTitle")}>
            {t("auth.signIn.sessionExpiredBody")}
          </Alert>
        )}
        {/* #131: accept-invite's own auto-login can fail even though the account was
            genuinely created -- land here instead of a dead end. */}
        {accountCreated === "1" && (
          <Alert tone="success" title={t("auth.signIn.accountCreatedTitle")}>
            {t("auth.signIn.accountCreatedBody")}
          </Alert>
        )}
        <LoginForm next={safeNext} />
      </div>
    </AuthShell>
  );
}
