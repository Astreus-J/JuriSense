import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { AcceptInviteForm } from "@/components/auth/AcceptInviteForm";
import { AuthShell } from "@/components/auth/AuthShell";
import { Alert } from "@/components/ui/Alert";
import { getSession } from "@/lib/auth/session";

export const metadata: Metadata = {
  title: "Accept invitation — JuriSense Gate",
  description: "Accept your invitation to JuriSense Gate.",
};

interface AcceptInvitePageProps {
  searchParams: Promise<{ token?: string }>;
}

export default async function AcceptInvitePage({ searchParams }: AcceptInvitePageProps) {
  const { token } = await searchParams;

  const session = await getSession();
  if (session) redirect("/dashboard");

  if (!token) {
    return (
      <AuthShell heading="Invitation link missing">
        <Alert tone="danger" title="This link is missing its invitation token.">
          Open the invitation link from your email again, or ask your admin to resend it.
        </Alert>
      </AuthShell>
    );
  }

  return (
    <AuthShell
      heading="Accept your invitation"
      subtext="Choose a password to finish setting up your account."
    >
      <AcceptInviteForm token={token} />
    </AuthShell>
  );
}
