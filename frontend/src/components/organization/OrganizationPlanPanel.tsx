import { PLAN_LABELS } from "@/lib/organization/types";
import type { Organization } from "@/lib/organization/types";

interface OrganizationPlanPanelProps {
  organization: Organization;
}

function formatLimit(value: number | null): string {
  return value === null ? "Unlimited" : value.toLocaleString();
}

/**
 * Display-only, for every viewer — there is no `PATCH /organizations/me` endpoint yet (the
 * org's own plan/name can't be self-service changed), so this never renders edit controls,
 * not even for an admin viewer. The distinction this screen actually cares about is whether
 * the *team* section below it renders (`getOrganizationPermissions(role).canManageTeam`),
 * not this panel.
 */
export function OrganizationPlanPanel({ organization }: OrganizationPlanPanelProps) {
  const usageItems = [
    {
      label: "Seats",
      value: `${organization.activeUserCount} / ${formatLimit(organization.userLimit)}`,
    },
    { label: "Suppliers", value: formatLimit(organization.supplierLimit) },
    {
      label: "Storage",
      value:
        organization.storageLimitGb === null
          ? "Unlimited"
          : `${organization.storageLimitGb.toLocaleString()} GB`,
    },
    { label: "AI executions / month", value: formatLimit(organization.aiExecutionLimit) },
  ];

  return (
    <section aria-label="Plan and usage" className="space-y-3">
      <div className="flex flex-wrap items-baseline gap-x-3">
        <h2 className="text-base font-semibold text-foreground">{organization.name}</h2>
        <p className="text-sm text-foreground-muted">{PLAN_LABELS[organization.plan]} plan</p>
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
