import { INTL_LOCALES } from "@/lib/i18n/config";
import { getI18n } from "@/lib/i18n/server";
import type { Translator } from "@/lib/i18n/translate";
import type { Organization } from "@/lib/organization/types";

interface OrganizationPlanPanelProps {
  organization: Organization;
}

function formatLimit(value: number | null, { t, locale }: Translator): string {
  return value === null
    ? t("organization.plan.unlimited")
    : value.toLocaleString(INTL_LOCALES[locale]);
}

/**
 * Display-only, for every viewer — there is no `PATCH /organizations/me` endpoint yet (the
 * org's own plan/name can't be self-service changed), so this never renders edit controls,
 * not even for an admin viewer. The distinction this screen actually cares about is whether
 * the *team* section below it renders (`getOrganizationPermissions(role).canManageTeam`),
 * not this panel.
 */
export async function OrganizationPlanPanel({ organization }: OrganizationPlanPanelProps) {
  const i18n = await getI18n();
  const { t, locale } = i18n;
  const usageItems = [
    {
      label: t("organization.plan.seats"),
      value: `${organization.activeUserCount} / ${formatLimit(organization.userLimit, i18n)}`,
    },
    { label: t("organization.plan.suppliers"), value: formatLimit(organization.supplierLimit, i18n) },
    {
      label: t("organization.plan.storage"),
      value:
        organization.storageLimitGb === null
          ? t("organization.plan.unlimited")
          : `${organization.storageLimitGb.toLocaleString(INTL_LOCALES[locale])} GB`,
    },
    {
      label: t("organization.plan.aiExecutions"),
      value: formatLimit(organization.aiExecutionLimit, i18n),
    },
  ];

  return (
    <section aria-label={t("organization.plan.aria")} className="space-y-3">
      <div className="flex flex-wrap items-baseline gap-x-3">
        <h2 className="text-base font-semibold text-foreground">{organization.name}</h2>
        <p className="text-sm text-foreground-muted">{t("organization.plan.planName", { plan: t(`status.plan.${organization.plan}`) })}</p>
      </div>

      <dl className="grid grid-cols-2 gap-px overflow-hidden rounded-lg border border-border bg-border sm:grid-cols-4">
        {usageItems.map((item) => (
          <div key={item.label} className="bg-surface px-4 py-3">
            <dt className="text-xs text-foreground-muted">{item.label}</dt>
            <dd className="mt-0.5 text-lg font-semibold tabular-nums text-foreground">{item.value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
