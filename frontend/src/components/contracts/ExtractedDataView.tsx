import type { ReactNode } from "react";
import { AlertTriangle, CheckCircle2, SquarePen } from "lucide-react";

import { Badge } from "@/components/ui/Badge";
import { formatConfidence, formatCurrency, formatDate } from "@/lib/format";
import type { ContractFields, ExtractedLeaf } from "@/lib/contracts/types";

interface ExtractedDataViewProps {
  fields: ContractFields;
  /** Dotted paths currently below the confidence threshold — drives the per-field
   * "Needs review" visual treatment below (persona: "Never communicate status by color
   * alone" — every flagged field pairs an icon, a label, *and* its actual confidence
   * number, not just a red tint). */
  needsConfirmationPaths: string[];
}

function formatPlainValue(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "number") return new Intl.NumberFormat(undefined).format(value);
  return String(value);
}

function ConfidenceIndicator({
  leaf,
  flagged,
}: {
  leaf: ExtractedLeaf;
  flagged: boolean;
}) {
  if (flagged) {
    return (
      <Badge tone="warning" icon={<AlertTriangle className="size-3" aria-hidden="true" />}>
        Needs review · {formatConfidence(leaf.confidence)}
      </Badge>
    );
  }
  if (leaf.human_corrected) {
    return (
      <Badge tone="info" icon={<SquarePen className="size-3" aria-hidden="true" />}>
        Corrected
      </Badge>
    );
  }
  if (leaf.human_confirmed) {
    return (
      <Badge tone="success" icon={<CheckCircle2 className="size-3" aria-hidden="true" />}>
        Confirmed
      </Badge>
    );
  }
  return (
    <span className="text-xs font-normal text-foreground-muted">
      {formatConfidence(leaf.confidence)} confidence
    </span>
  );
}

interface FieldRowProps {
  label: string;
  leaf: ExtractedLeaf | null | undefined;
  path: string;
  needsConfirmationPaths: string[];
  format?: (value: unknown) => string;
}

/** One AI-extracted fact: label, formatted value, and its confidence — omitted entirely
 * (not rendered as an empty "—" row) when the AI didn't extract this field at all, since a
 * contract legitimately may not mention every possible term (persona: "progressive
 * disclosure over information overload"). */
function FieldRow({ label, leaf, path, needsConfirmationPaths, format = formatPlainValue }: FieldRowProps) {
  if (!leaf) return null;
  const flagged = needsConfirmationPaths.includes(path);
  return (
    <div>
      <dt className="text-xs font-medium uppercase tracking-wide text-foreground-muted">{label}</dt>
      <dd className="mt-1 flex flex-wrap items-center gap-2 text-sm font-medium text-foreground">
        <span>{format(leaf.value)}</span>
        <ConfidenceIndicator leaf={leaf} flagged={flagged} />
      </dd>
    </div>
  );
}

function Card({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="space-y-3 rounded-xl border border-border bg-surface p-6">
      <h3 className="text-sm font-semibold text-foreground">{title}</h3>
      {children}
    </section>
  );
}

export function ExtractedDataView({ fields, needsConfirmationPaths }: ExtractedDataViewProps) {
  const parties = fields.parties?.value ?? [];
  const obligations = fields.obligations ?? [];
  const deadlines = fields.deadlines ?? [];
  const guarantees = fields.guarantees ?? [];
  const penalties = fields.penalties ?? [];
  const subprocessors = fields.subprocessors ?? [];
  const hasAdditional = guarantees.length > 0 || penalties.length > 0 || subprocessors.length > 0;
  const hasAnyField =
    Boolean(fields.contract_type) ||
    Boolean(fields.parties) ||
    Boolean(fields.value?.amount) ||
    Boolean(fields.value?.currency) ||
    Boolean(fields.duration?.start_date) ||
    Boolean(fields.duration?.end_date) ||
    Boolean(fields.duration?.auto_renewal) ||
    Boolean(fields.termination?.notice_period_days) ||
    Boolean(fields.termination?.termination_for_convenience) ||
    Boolean(fields.termination?.termination_for_cause_conditions) ||
    Boolean(fields.liability?.type) ||
    Boolean(fields.liability?.cap) ||
    Boolean(fields.privacy?.processes_personal_data) ||
    Boolean(fields.privacy?.dpa_present) ||
    Boolean(fields.jurisdiction) ||
    obligations.length > 0 ||
    deadlines.length > 0 ||
    hasAdditional;

  if (!hasAnyField) {
    return (
      <p className="rounded-xl border border-dashed border-border bg-surface px-6 py-10 text-center text-sm text-foreground-muted">
        JuriSense didn&apos;t extract any structured fields from this document. This can
        happen with scanned, low-quality, or unusually formatted files — try uploading a
        clearer copy as a new version.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      {(fields.contract_type || fields.jurisdiction) && (
        <dl className="grid gap-4 rounded-xl border border-border bg-surface p-6 sm:grid-cols-2">
          <FieldRow
            label="Contract type"
            leaf={fields.contract_type}
            path="contract_type"
            needsConfirmationPaths={needsConfirmationPaths}
          />
          <FieldRow
            label="Jurisdiction"
            leaf={fields.jurisdiction}
            path="jurisdiction"
            needsConfirmationPaths={needsConfirmationPaths}
          />
        </dl>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        {(fields.value?.amount || fields.value?.currency) && (
          <Card title="Contract value">
            <dl className="grid gap-4 sm:grid-cols-2">
              <FieldRow
                label="Amount"
                leaf={fields.value?.amount}
                path="value.amount"
                needsConfirmationPaths={needsConfirmationPaths}
                format={(value) =>
                  formatCurrency(value as number, fields.value?.currency?.value as string | undefined)
                }
              />
              <FieldRow
                label="Currency"
                leaf={fields.value?.currency}
                path="value.currency"
                needsConfirmationPaths={needsConfirmationPaths}
              />
            </dl>
          </Card>
        )}

        {(fields.duration?.start_date || fields.duration?.end_date || fields.duration?.auto_renewal) && (
          <Card title="Duration">
            <dl className="grid gap-4 sm:grid-cols-2">
              <FieldRow
                label="Start date"
                leaf={fields.duration?.start_date}
                path="duration.start_date"
                needsConfirmationPaths={needsConfirmationPaths}
                format={(value) => formatDate(value as string)}
              />
              <FieldRow
                label="End date"
                leaf={fields.duration?.end_date}
                path="duration.end_date"
                needsConfirmationPaths={needsConfirmationPaths}
                format={(value) => formatDate(value as string)}
              />
              <FieldRow
                label="Auto-renewal"
                leaf={fields.duration?.auto_renewal}
                path="duration.auto_renewal"
                needsConfirmationPaths={needsConfirmationPaths}
              />
            </dl>
          </Card>
        )}

        {(fields.termination?.notice_period_days ||
          fields.termination?.termination_for_convenience ||
          fields.termination?.termination_for_cause_conditions) && (
          <Card title="Termination">
            <dl className="grid gap-4 sm:grid-cols-2">
              <FieldRow
                label="Notice period (days)"
                leaf={fields.termination?.notice_period_days}
                path="termination.notice_period_days"
                needsConfirmationPaths={needsConfirmationPaths}
              />
              <FieldRow
                label="Termination for convenience"
                leaf={fields.termination?.termination_for_convenience}
                path="termination.termination_for_convenience"
                needsConfirmationPaths={needsConfirmationPaths}
              />
              <FieldRow
                label="Termination for cause"
                leaf={fields.termination?.termination_for_cause_conditions}
                path="termination.termination_for_cause_conditions"
                needsConfirmationPaths={needsConfirmationPaths}
              />
            </dl>
          </Card>
        )}

        {(fields.liability?.type || fields.liability?.cap) && (
          <Card title="Liability">
            <dl className="grid gap-4 sm:grid-cols-2">
              <FieldRow
                label="Type"
                leaf={fields.liability?.type}
                path="liability.type"
                needsConfirmationPaths={needsConfirmationPaths}
              />
              <FieldRow
                label="Cap"
                leaf={fields.liability?.cap}
                path="liability.cap"
                needsConfirmationPaths={needsConfirmationPaths}
              />
            </dl>
          </Card>
        )}

        {(fields.privacy?.processes_personal_data || fields.privacy?.dpa_present) && (
          <Card title="Privacy / DPA">
            <dl className="grid gap-4 sm:grid-cols-2">
              <FieldRow
                label="Processes personal data"
                leaf={fields.privacy?.processes_personal_data}
                path="privacy.processes_personal_data"
                needsConfirmationPaths={needsConfirmationPaths}
              />
              <FieldRow
                label="DPA present"
                leaf={fields.privacy?.dpa_present}
                path="privacy.dpa_present"
                needsConfirmationPaths={needsConfirmationPaths}
              />
            </dl>
          </Card>
        )}
      </div>

      {parties.length > 0 && (
        <Card title="Parties">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-xs uppercase tracking-wide text-foreground-muted">
                <tr>
                  <th className="py-1.5 pr-4 font-medium">Role</th>
                  <th className="py-1.5 pr-4 font-medium">Name</th>
                  <th className="py-1.5 pr-4 font-medium">Tax ID</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {parties.map((party, index) => (
                  <tr key={index}>
                    <td className="py-1.5 pr-4 capitalize text-foreground-muted">{party.role}</td>
                    <td className="py-1.5 pr-4 font-medium text-foreground">{party.name}</td>
                    <td className="py-1.5 pr-4 text-foreground-muted">{party.tax_id ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {fields.parties && (
            <div className="flex items-center gap-2 text-xs">
              <span className="font-medium uppercase tracking-wide text-foreground-muted">
                Extraction confidence
              </span>
              <ConfidenceIndicator
                leaf={fields.parties}
                flagged={needsConfirmationPaths.includes("parties")}
              />
            </div>
          )}
        </Card>
      )}

      {obligations.length > 0 && (
        <Card title="Obligations">
          <ul className="space-y-2">
            {obligations.map((leaf, index) => (
              <li key={index} className="flex flex-wrap items-center gap-2 text-sm">
                <span className="text-foreground">{leaf.value as string}</span>
                <ConfidenceIndicator
                  leaf={leaf}
                  flagged={needsConfirmationPaths.includes(`obligations[${index}]`)}
                />
              </li>
            ))}
          </ul>
        </Card>
      )}

      {deadlines.length > 0 && (
        <Card title="Deadlines">
          <ul className="space-y-2">
            {deadlines.map((deadline, index) => (
              <li key={index} className="flex flex-wrap items-center gap-2 text-sm">
                <span className="text-foreground">{deadline.description}</span>
                {deadline.date && (
                  <>
                    <span className="text-foreground-muted">— {formatDate(deadline.date.value)}</span>
                    <ConfidenceIndicator
                      leaf={deadline.date}
                      flagged={needsConfirmationPaths.includes(`deadlines[${index}].date`)}
                    />
                  </>
                )}
              </li>
            ))}
          </ul>
        </Card>
      )}

      {hasAdditional && (
        <Card title="Additional details">
          <div className="grid gap-4 sm:grid-cols-3">
            {guarantees.length > 0 && (
              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-foreground-muted">
                  Guarantees
                </p>
                <ul className="mt-1 space-y-1 text-sm text-foreground">
                  {guarantees.map((leaf, index) => (
                    <li key={index}>{leaf.value as string}</li>
                  ))}
                </ul>
              </div>
            )}
            {penalties.length > 0 && (
              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-foreground-muted">
                  Penalties
                </p>
                <ul className="mt-1 space-y-1 text-sm text-foreground">
                  {penalties.map((leaf, index) => (
                    <li key={index}>{leaf.value as string}</li>
                  ))}
                </ul>
              </div>
            )}
            {subprocessors.length > 0 && (
              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-foreground-muted">
                  Subprocessors
                </p>
                <ul className="mt-1 space-y-1 text-sm text-foreground">
                  {subprocessors.map((leaf, index) => (
                    <li key={index}>{leaf.value as string}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </Card>
      )}
    </div>
  );
}
