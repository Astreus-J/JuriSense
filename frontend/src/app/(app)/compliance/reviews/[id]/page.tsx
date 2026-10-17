import { notFound } from "next/navigation";

import { Alert } from "@/components/ui/Alert";
import { PageHeader } from "@/components/ui/PageHeader";
import { ComplianceReviewResults } from "@/components/compliance/ComplianceReviewResults";
import { ApiError } from "@/lib/auth/backend";
import { readAccessToken } from "@/lib/auth/cookies";
import { requireSession } from "@/lib/auth/session";
import { getI18n, pageTitle } from "@/lib/i18n/server";
import type { Translator } from "@/lib/i18n/translate";
import { getComplianceReview } from "@/lib/compliance/backend";
import { getCompliancePermissions } from "@/lib/compliance/permissions";

export const generateMetadata = pageTitle("meta.complianceReview");

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
  const i18n = await getI18n();
  const { t } = i18n;
  const { id } = await params;
  const { contractId } = await searchParams;
  const accessToken = (await readAccessToken())!;
  const permissions = getCompliancePermissions(user.role);

  if (!permissions.canRead) {
    return (
      <div className="space-y-5">
        <PageHeader title={t("compliance.title")} breadcrumbs={breadcrumbsFor(i18n, contractId)} />
        <Alert tone="danger" title={t("compliance.noAccessTitle")}>
          {t("compliance.noAccessBody")}
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
          <PageHeader title={t("compliance.title")} breadcrumbs={breadcrumbsFor(i18n, contractId)} />
          <Alert tone="danger" title={t("compliance.noAccessThisTitle")}>
            {t("compliance.noAccessBody")}
          </Alert>
        </div>
      );
    }
    throw error;
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={t("compliance.title")}
        description={t("compliance.description")}
        breadcrumbs={breadcrumbsFor(i18n, contractId)}
      />
      <ComplianceReviewResults detail={detail} />
    </div>
  );
}

function breadcrumbsFor({ t }: Translator, contractId?: string) {
  return contractId
    ? [
        { label: t("nav.contracts"), href: "/contracts" },
        { label: t("compliance.breadcrumbContract"), href: `/contracts/${contractId}` },
        { label: t("compliance.title") },
      ]
    : [{ label: t("compliance.title") }];
}
