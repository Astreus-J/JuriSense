import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { Alert } from "@/components/ui/Alert";
import { PageHeader } from "@/components/ui/PageHeader";
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
      <div className="space-y-5">
        <PageHeader title="Compliance review" breadcrumbs={breadcrumbsFor(contractId)} />
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
        <div className="space-y-5">
          <PageHeader title="Compliance review" breadcrumbs={breadcrumbsFor(contractId)} />
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
      <PageHeader
        title="Compliance review"
        description="The decision, the risks behind it, and every rule that was evaluated, each with its evidence."
        breadcrumbs={breadcrumbsFor(contractId)}
      />
      <ComplianceReviewResults detail={detail} />
    </div>
  );
}

function breadcrumbsFor(contractId?: string) {
  return contractId
    ? [
        { label: "Contracts", href: "/contracts" },
        { label: "Contract", href: `/contracts/${contractId}` },
        { label: "Compliance review" },
      ]
    : [{ label: "Compliance review" }];
}
