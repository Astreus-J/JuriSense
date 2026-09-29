import { cn } from "@/lib/cn";
import {
  ADDRESS_FLAG_LABELS,
  REGISTRY_STATUS_LABELS,
} from "@/lib/suppliers/types";
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
      <dt className="text-xs font-medium uppercase tracking-wide text-foreground-muted">{label}</dt>
      <dd className={cn("mt-1 text-sm font-medium", toneClass)}>{value}</dd>
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
export function SupplierProfileCard({ profile }: SupplierProfileCardProps) {
  if (!profile) {
    return (
      <section className="rounded-xl border border-dashed border-border bg-surface px-6 py-10 text-center">
        <p className="text-sm font-medium text-foreground">Verification in progress</p>
        <p className="mx-auto mt-1 max-w-sm text-sm text-foreground-muted">
          This supplier hasn&apos;t completed a verification check yet. Its profile will appear
          here once the check finishes — usually within a few minutes. Use &quot;Run
          verification check&quot; below if it has been longer than that.
        </p>
      </section>
    );
  }

  return (
    <section className="space-y-4 rounded-xl border border-border bg-surface p-6">
      <h2 className="text-sm font-semibold text-foreground">Verification profile</h2>

      <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <ProfileField label="Registry status" value={REGISTRY_STATUS_LABELS[profile.registryStatus]} />
        <ProfileField
          label="Sanctions check"
          value={profile.sanctionsHit ? "Hit" : "Clear"}
          tone={profile.sanctionsHit ? "danger" : "success"}
        />
        <ProfileField
          label="Activity (CNAE) match"
          value={profile.activityMismatch ? "Mismatch" : "Consistent"}
          tone={profile.activityMismatch ? "warning" : "success"}
        />
        <ProfileField
          label="Address"
          value={ADDRESS_FLAG_LABELS[profile.addressFlag]}
          tone={profile.addressFlag === "flagged" ? "warning" : undefined}
        />
        {profile.cnaeCode && (
          <ProfileField
            label="CNAE"
            value={`${profile.cnaeCode}${profile.cnaeDescription ? ` — ${profile.cnaeDescription}` : ""}`}
          />
        )}
      </dl>

      {profile.sanctionsHit && profile.sanctionsDetail.length > 0 && (
        <div className="space-y-2 rounded-lg border border-danger-border bg-danger-surface p-4">
          <p className="text-sm font-semibold text-danger">Sanctions matches</p>
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

      <details className="rounded-lg border border-border bg-surface-muted p-4 text-sm">
        <summary className="cursor-pointer font-medium text-foreground">
          Raw registry data
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
