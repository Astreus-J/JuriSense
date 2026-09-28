import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { AuthShell } from "@/components/auth/AuthShell";
import { LoginForm } from "@/components/auth/LoginForm";
import { Alert } from "@/components/ui/Alert";
import { getSession } from "@/lib/auth/session";

export const metadata: Metadata = {
  title: "Sign in — JuriSense Gate",
  description: "Sign in to JuriSense Gate.",
};

function isSafeNextPath(next: string | undefined): next is string {
  return typeof next === "string" && next.startsWith("/") && !next.startsWith("//");
}

interface LoginPageProps {
  searchParams: Promise<{ next?: string; expired?: string }>;
}

export default async function LoginPage({ searchParams }: LoginPageProps) {
  const { next, expired } = await searchParams;
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
        <LoginForm next={safeNext} />
      </div>
    </AuthShell>
  );
}
