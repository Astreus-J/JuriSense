import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft } from "lucide-react";

import { Alert } from "@/components/ui/Alert";
import { ComplianceReviewResults } from "@/components/compliance/ComplianceReviewResults";
import { ApiError } from "@/lib/auth/backend";
import { readAccessToken } from "@/lib/auth/cookies";
import { requireSession } from "@/lib/auth/session";
import { getComplianceReview } from "@/lib/compliance/backend";
import { getCompliancePermissions } from "@/lib/compliance/permissions";

export const metadata: Metadata = { title: "Compliance review — JuriSense Gate" };

interface ComplianceReviewPageProps {
  // Next 16: `params`/`searchParams` are Promises.
  params: Promise<{ id: string }>;
  searchParams: Promise<{ contractId?: string }>;
}

/**
 * #62: the compliance review results screen. Not a top-level nav item — Compliance has no
 * `ModuleKey` entry in `src/lib/navigation/modules.ts` by design; this screen is reached from
 * a Contract's detail page (`TriggerComplianceReviewButton`/`ComplianceReviewHistory`), hence
 * the optional `?contractId=` back-link instead of a reverse lookup.
 */
export default async function ComplianceReviewPage({
  params,
  searchParams,
}: ComplianceReviewPageProps) {
  const user = await requireSession();
  const { id } = await params;
  const { contractId } = await searchParams;
  const accessToken = (await readAccessToken())!;
  const permissions = getCompliancePermissions(user.role);

  if (!permissions.canRead) {
    return (
      <div className="space-y-6">
        <BackLink contractId={contractId} />
        <Alert tone="danger" title="You don't have access to compliance reviews.">
          Ask an administrator to grant you the &quot;compliance reviews&quot; read permission
          for this organization.
        </Alert>
      </div>
    );
  }

  let detail;
  try {
    detail = await getComplianceReview(accessToken, id);
  } catch (error) {
    // A malformed id is treated the same as "no such review" — see
    // `suppliers/[id]/page.tsx`'s identical note.
    if (error instanceof ApiError && (error.status === 404 || error.status === 400)) notFound();
    if (error instanceof ApiError && error.status === 403) {
      return (
        <div className="space-y-6">
          <BackLink contractId={contractId} />
          <Alert tone="danger" title="You don't have access to this compliance review.">
            Ask an administrator to grant you the &quot;compliance reviews&quot; read
            permission for this organization.
          </Alert>
        </div>
      );
    }
    throw error;
  }

  return (
    <div className="space-y-6">
      <BackLink contractId={contractId} />
      <h1 className="text-2xl font-semibold tracking-tight text-foreground">
        Compliance review
      </h1>
      <ComplianceReviewResults detail={detail} />
    </div>
  );
}

function BackLink({ contractId }: { contractId?: string }) {
  if (!contractId) return null;
  return (
    <Link
      href={`/contracts/${contractId}`}
      className="inline-flex items-center gap-1 text-sm font-medium text-foreground-muted hover:text-foreground"
    >
      <ArrowLeft className="size-4" aria-hidden="true" />
      Back to contract
    </Link>
  );
}
