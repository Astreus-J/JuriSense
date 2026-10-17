import { notFound } from "next/navigation";

import { Alert } from "@/components/ui/Alert";
import { PageHeader } from "@/components/ui/PageHeader";
import { DecisionPassportView } from "@/components/evidence/DecisionPassportView";
import { ApiError } from "@/lib/auth/backend";
import { readAccessToken } from "@/lib/auth/cookies";
import { requireSession } from "@/lib/auth/session";
import { getI18n, pageTitle } from "@/lib/i18n/server";
import { getDecisionPassport } from "@/lib/evidence/backend";
import { getEvidencePermissions } from "@/lib/evidence/permissions";

export const generateMetadata = pageTitle("meta.decision");

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
  const { t } = await getI18n();
  const breadcrumbs = [
    { label: t("nav.evidence"), href: "/evidence" },
    { label: t("decisions.title") },
  ];
  const { id } = await params;
  const accessToken = (await readAccessToken())!;
  const permissions = getEvidencePermissions(user.role);

  if (!permissions.canRead) {
    return (
      <div className="space-y-5">
        <PageHeader title={t("decisions.title")} breadcrumbs={breadcrumbs} />
        <Alert tone="danger" title={t("decisions.noAccessTitle")}>
          {t("decisions.noAccessBody")}
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
        <div className="space-y-5">
          <PageHeader title={t("decisions.title")} breadcrumbs={breadcrumbs} />
          <Alert tone="danger" title={t("decisions.noAccessThisTitle")}>
            {t("decisions.noAccessBody")}
          </Alert>
        </div>
      );
    }
    throw error;
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={t("decisions.title")}
        description={t("decisions.description")}
        breadcrumbs={breadcrumbs}
      />
      <DecisionPassportView passport={passport} />
    </div>
  );
}
