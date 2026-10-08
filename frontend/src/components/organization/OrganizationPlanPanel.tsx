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
    <div className="rounded-xl border border-border bg-surface p-6">
      <div>
        <h2 className="text-lg font-semibold text-foreground">{organization.name}</h2>
        <p className="mt-1 text-sm text-foreground-muted">
          {PLAN_LABELS[organization.plan]} plan
        </p>
      </div>

      <dl className="mt-6 grid grid-cols-2 gap-6 sm:grid-cols-4">
        {usageItems.map((item) => (
          <div key={item.label}>
            <dt className="text-xs font-medium uppercase tracking-wide text-foreground-muted">
              {item.label}
            </dt>
            <dd className="mt-1 text-xl font-semibold text-foreground">{item.value}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
