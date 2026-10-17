import { Hourglass } from "lucide-react";

import { EmptyState } from "@/components/ui/EmptyState";
import { cn } from "@/lib/cn";
import { getI18n } from "@/lib/i18n/server";
import type { SupplierProfile } from "@/lib/suppliers/types";

interface SupplierProfileCardProps {
  profile: SupplierProfile | null;
}

function formatKey(key: string): string {
  return key.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());
}

function ProfileField({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone?: "success" | "warning" | "danger";
}) {
  const toneClass =
    tone === "danger"
      ? "text-danger"
      : tone === "warning"
        ? "text-warning"
        : tone === "success"
          ? "text-success"
          : "text-foreground";

  return (
    <div>
      <dt className="text-xs text-foreground-muted">{label}</dt>
      <dd className={cn("mt-0.5 text-sm font-medium", toneClass)}>{value}</dd>
    </div>
  );
}

/**
 * SUP-003's normalized SupplierProfile. `sanctionsHit` is BR-SUP-004's compliance-critical
 * signal — the caller (the detail page) renders a full-width danger `Alert` above the whole
 * page when it's true, on top of this card's own "Sanctions matches" section, so it can
 * never be missed by a busy layout (persona: "not a minor badge... do not let a busy layout
 * bury it").
 */
export async function SupplierProfileCard({ profile }: SupplierProfileCardProps) {
  const { t } = await getI18n();
  if (!profile) {
    return (
      <EmptyState
        icon={Hourglass}
        title={t("suppliers.profile.pendingTitle")}
        description={t("suppliers.profile.pendingBody")}
      />
    );
  }

  return (
    <section className="space-y-4">
      <h2 className="text-base font-semibold text-foreground">{t("suppliers.profile.title")}</h2>

      <dl className="grid gap-x-6 gap-y-4 border-y border-border py-4 sm:grid-cols-2 lg:grid-cols-4">
        <ProfileField label={t("suppliers.profile.registryStatus")} value={t(`status.registry.${profile.registryStatus}`)} />
        <ProfileField
          label={t("suppliers.profile.sanctionsCheck")}
          value={profile.sanctionsHit ? t("suppliers.profile.hit") : t("suppliers.profile.clear")}
          tone={profile.sanctionsHit ? "danger" : "success"}
        />
        <ProfileField
          label={t("suppliers.profile.activityMatch")}
          value={profile.activityMismatch ? t("suppliers.profile.mismatch") : t("suppliers.profile.consistent")}
          tone={profile.activityMismatch ? "warning" : "success"}
        />
        <ProfileField
          label={t("suppliers.profile.address")}
          value={t(`status.addressFlag.${profile.addressFlag}`)}
          tone={profile.addressFlag === "flagged" ? "warning" : undefined}
        />
        {profile.cnaeCode && (
          <ProfileField
            label={t("suppliers.profile.cnae")}
            value={`${profile.cnaeCode}${profile.cnaeDescription ? ` — ${profile.cnaeDescription}` : ""}`}
          />
        )}
      </dl>

      {profile.sanctionsHit && profile.sanctionsDetail.length > 0 && (
        <div className="space-y-2 rounded-md border border-danger-border bg-danger-surface p-3">
          <p className="text-sm font-semibold text-danger">{t("suppliers.profile.sanctionsMatches")}</p>
          <ul className="space-y-2">
            {profile.sanctionsDetail.map((entry, index) => (
              <li
                key={index}
                className="space-y-0.5 rounded border border-danger-border/60 bg-surface px-3 py-2 text-xs"
              >
                {Object.entries(entry).map(([key, value]) => (
                  <div key={key} className="flex gap-1.5">
                    <span className="font-medium text-foreground">{formatKey(key)}:</span>
                    <span className="text-foreground-muted">{String(value)}</span>
                  </div>
                ))}
              </li>
            ))}
          </ul>
        </div>
      )}

      <details className="rounded-md border border-border p-3 text-sm">
        <summary className="cursor-pointer font-medium text-foreground">
          {t("suppliers.profile.rawData")}
        </summary>
        <pre className="mt-2 overflow-x-auto whitespace-pre-wrap text-xs text-foreground-muted">
          {JSON.stringify(
            {
              corporateStructure: profile.corporateStructure,
              responsibleParties: profile.responsibleParties,
              address: profile.address,
            },
            null,
            2,
          )}
        </pre>
      </details>
    </section>
  );
}
