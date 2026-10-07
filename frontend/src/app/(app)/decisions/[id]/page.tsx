import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft } from "lucide-react";

import { Alert } from "@/components/ui/Alert";
import { DecisionPassportView } from "@/components/evidence/DecisionPassportView";
import { ApiError } from "@/lib/auth/backend";
import { readAccessToken } from "@/lib/auth/cookies";
import { requireSession } from "@/lib/auth/session";
import { getDecisionPassport } from "@/lib/evidence/backend";
import { getEvidencePermissions } from "@/lib/evidence/permissions";

export const metadata: Metadata = { title: "Decision Passport — JuriSense Gate" };

interface DecisionPassportPageProps {
  // Next 16: `params` is a Promise.
  params: Promise<{ id: string }>;
}

/**
 * STORY-7.3.1: the Decision Passport view. Reached by Decision id — there is no "browse all
 * decisions" list in this story's scope, so the `/evidence` landing page (`NAV_ITEMS.evidence`)
 * offers a lookup form instead, mirroring how `compliance/reviews/[id]` has no reverse index
 * of its own either.
 */
export default async function DecisionPassportPage({ params }: DecisionPassportPageProps) {
  const user = await requireSession();
  const { id } = await params;
  const accessToken = (await readAccessToken())!;
  const permissions = getEvidencePermissions(user.role);

  if (!permissions.canRead) {
    return (
      <div className="space-y-6">
        <BackLink />
        <Alert tone="danger" title="You don't have access to the Decision Passport.">
          Ask an administrator to grant you the &quot;evidence&quot; read permission for this
          organization.
        </Alert>
      </div>
    );
  }

  let passport;
  try {
    passport = await getDecisionPassport(accessToken, id);
  } catch (error) {
    // A malformed id is treated the same as "no such decision" — see
    // `suppliers/[id]/page.tsx`'s identical note.
    if (error instanceof ApiError && (error.status === 404 || error.status === 400)) notFound();
    if (error instanceof ApiError && error.status === 403) {
      return (
        <div className="space-y-6">
          <BackLink />
          <Alert tone="danger" title="You don't have access to this decision.">
            Ask an administrator to grant you the &quot;evidence&quot; read permission for this
            organization.
          </Alert>
        </div>
      );
    }
    throw error;
  }

  return (
    <div className="space-y-6">
      <BackLink />
      <h1 className="text-2xl font-semibold tracking-tight text-foreground">Decision Passport</h1>
      <DecisionPassportView passport={passport} />
    </div>
  );
}

function BackLink() {
  return (
    <Link
      href="/evidence"
      className="inline-flex items-center gap-1 text-sm font-medium text-foreground-muted hover:text-foreground"
    >
      <ArrowLeft className="size-4" aria-hidden="true" />
      Back to Evidence & Audit
    </Link>
  );
}
