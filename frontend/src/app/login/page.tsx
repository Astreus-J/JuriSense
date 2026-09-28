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
  if (typeof next !== "string" || next.length === 0) return false;
  if (next[0] !== "/") return false;
  // A single leading "/" is required, but a *second* "/" or a "\" right
  // after it produces a scheme-relative URL once a browser normalizes it
  // (both "//evil.com" and "/\evil.com" resolve to https://evil.com) --
  // reject both, plus any embedded backslash anywhere as defense in depth
  // (found in security review: the original check only rejected "//").
  if (/^\/[/\\]/.test(next) || next.includes("\\")) return false;
  return true;
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
