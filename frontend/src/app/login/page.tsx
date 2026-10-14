import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { AuthShell } from "@/components/auth/AuthShell";
import { LoginForm } from "@/components/auth/LoginForm";
import { Alert } from "@/components/ui/Alert";
import { isSafeNextPath } from "@/lib/auth/safe-redirect";
import { getSession } from "@/lib/auth/session";

export const metadata: Metadata = {
  title: "Sign in — JuriSense Gate",
  description: "Sign in to JuriSense Gate.",
};

interface LoginPageProps {
  searchParams: Promise<{ next?: string; expired?: string; accountCreated?: string }>;
}

export default async function LoginPage({ searchParams }: LoginPageProps) {
  const { next, expired, accountCreated } = await searchParams;
  const safeNext = isSafeNextPath(next) ? next : "/dashboard";

  // Already signed in: no reason to show the login form again.
  const session = await getSession();
  if (session) redirect(safeNext);

  return (
    <AuthShell
      heading="Sign in"
      subtext="Vendor, contract, and compliance decisions — evidence-backed, every time."
    >
      <div className="space-y-5">
        {expired === "1" && (
          <Alert tone="warning" title="Your session expired.">
            Sign in again to continue.
          </Alert>
        )}
        {/* #131: accept-invite's own auto-login can fail even though the account was
            genuinely created -- land here instead of a dead end. */}
        {accountCreated === "1" && (
          <Alert tone="success" title="Your account was created.">
            Sign in with the password you just chose to continue.
          </Alert>
        )}
        <LoginForm next={safeNext} />
      </div>
    </AuthShell>
  );
}
