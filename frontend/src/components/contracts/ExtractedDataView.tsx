import type { ReactNode } from "react";
import { AlertTriangle, CheckCircle2, SquarePen } from "lucide-react";

import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { formatConfidence, formatCurrency, formatDate } from "@/lib/format";
import { INTL_LOCALES } from "@/lib/i18n/config";
import { getI18n } from "@/lib/i18n/server";
import type { Translator } from "@/lib/i18n/translate";
import type { ContractFields, ExtractedLeaf } from "@/lib/contracts/types";

interface ExtractedDataViewProps {
  fields: ContractFields;
  /** Dotted paths currently below the confidence threshold — drives the per-field
   * "Needs review" visual treatment below (persona: "Never communicate status by color
   * alone" — every flagged field pairs an icon, a label, *and* its actual confidence
   * number, not just a red tint). */
  needsConfirmationPaths: string[];
}

function formatPlainValue(value: unknown, { t, locale }: Translator): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "boolean") return value ? t("contracts.confirm.yes") : t("contracts.confirm.no");
  if (typeof value === "number") return new Intl.NumberFormat(INTL_LOCALES[locale]).format(value);
  return String(value);
}

async function ConfidenceIndicator({
  leaf,
  flagged,
}: {
  leaf: ExtractedLeaf;
  flagged: boolean;
}) {
  const { t, locale } = await getI18n();
  if (flagged) {
    return (
      <Badge tone="warning" icon={<AlertTriangle className="size-3" aria-hidden="true" />}>
        {t("contracts.extracted.needsReview", { confidence: formatConfidence(leaf.confidence, locale) })}
      </Badge>
    );
  }
  if (leaf.human_corrected) {
    return (
      <Badge tone="info" icon={<SquarePen className="size-3" aria-hidden="true" />}>
        {t("contracts.extracted.corrected")}
      </Badge>
    );
  }
  if (leaf.human_confirmed) {
    return (
      <Badge tone="success" icon={<CheckCircle2 className="size-3" aria-hidden="true" />}>
        {t("contracts.extracted.confirmed")}
      </Badge>
    );
  }
  return (
    <span className="text-xs font-normal text-foreground-muted">
      {t("contracts.extracted.confidence", { confidence: formatConfidence(leaf.confidence, locale) })}
    </span>
  );
}

interface FieldRowProps {
  label: string;
  leaf: ExtractedLeaf | null | undefined;
  path: string;
  needsConfirmationPaths: string[];
  format?: (value: unknown, i18n: Translator) => string;
}

/** One AI-extracted fact: label, formatted value, and its confidence — omitted entirely
 * (not rendered as an empty "—" row) when the AI didn't extract this field at all, since a
 * contract legitimately may not mention every possible term (persona: "progressive
 * disclosure over information overload"). */
async function FieldRow({
  label,
  leaf,
  path,
  needsConfirmationPaths,
  format = formatPlainValue,
}: FieldRowProps) {
  if (!leaf) return null;
  const i18n = await getI18n();
  const flagged = needsConfirmationPaths.includes(path);
  return (
    <div>
      <dt className="text-xs text-foreground-muted">{label}</dt>
      <dd className="mt-0.5 flex flex-wrap items-center gap-2 text-sm font-medium text-foreground">
        <span>{format(leaf.value, i18n)}</span>
        <ConfidenceIndicator leaf={leaf} flagged={flagged} />
      </dd>
    </div>
  );
}

function Card({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="space-y-3 border-t border-border pt-3">
      <h3 className="text-sm font-semibold text-foreground">{title}</h3>
      {children}
    </section>
  );
}

export async function ExtractedDataView({ fields, needsConfirmationPaths }: ExtractedDataViewProps) {
  const i18n = await getI18n();
  const { t, locale } = i18n;
  // QA review (2026-10-17): `fields.parties.value`'s type is backend-side `Any`
  // (app/ai_services/domain/schema.py's ExtractedValue.value) -- the AI Gateway's JSON
  // Schema export loses the "array of {role,name,tax_id}" shape the prompt documents,
  // so a provider that doesn't follow the prose instruction exactly (confirmed with a
  // real extraction) can return a non-array value (e.g. a single summary string) that
  // passes backend validation but crashes `.map()` below. Never trust the shape without
  // checking it client-side, same principle as the rest of this view's confidence gate.
  const parties = Array.isArray(fields.parties?.value) ? fields.parties.value : [];
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
      <EmptyState
        title={t("contracts.extracted.emptyTitle")}
        description={t("contracts.extracted.emptyBody")}
      />
    );
  }

  return (
    <div className="space-y-6">
      <h2 className="text-base font-semibold text-foreground">{t("contracts.extracted.title")}</h2>
      {(fields.contract_type || fields.jurisdiction) && (
        <dl className="grid gap-4 sm:grid-cols-2">
          <FieldRow
            label={t("contracts.extracted.contractType")}
            leaf={fields.contract_type}
            path="contract_type"
            needsConfirmationPaths={needsConfirmationPaths}
          />
          <FieldRow
            label={t("contracts.extracted.jurisdiction")}
            leaf={fields.jurisdiction}
            path="jurisdiction"
            needsConfirmationPaths={needsConfirmationPaths}
          />
        </dl>
      )}

      <div className="grid gap-x-8 gap-y-6 md:grid-cols-2">
        {(fields.value?.amount || fields.value?.currency) && (
          <Card title={t("contracts.extracted.value")}>
            <dl className="grid gap-4 sm:grid-cols-2">
              <FieldRow
                label={t("contracts.extracted.amount")}
                leaf={fields.value?.amount}
                path="value.amount"
                needsConfirmationPaths={needsConfirmationPaths}
                format={(value) =>
                  formatCurrency(
                    value as number | null,
                    locale,
                    fields.value?.currency?.value as string | undefined,
                  )
                }
              />
              <FieldRow
                label={t("contracts.extracted.currency")}
                leaf={fields.value?.currency}
                path="value.currency"
                needsConfirmationPaths={needsConfirmationPaths}
              />
            </dl>
          </Card>
        )}

        {(fields.duration?.start_date || fields.duration?.end_date || fields.duration?.auto_renewal) && (
          <Card title={t("contracts.extracted.duration")}>
            <dl className="grid gap-4 sm:grid-cols-2">
              <FieldRow
                label={t("contracts.extracted.startDate")}
                leaf={fields.duration?.start_date}
                path="duration.start_date"
                needsConfirmationPaths={needsConfirmationPaths}
                format={(value) => formatDate(value as string, locale)}
              />
              <FieldRow
                label={t("contracts.extracted.endDate")}
                leaf={fields.duration?.end_date}
                path="duration.end_date"
                needsConfirmationPaths={needsConfirmationPaths}
                format={(value) => formatDate(value as string, locale)}
              />
              <FieldRow
                label={t("contracts.extracted.autoRenewal")}
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
          <Card title={t("contracts.extracted.termination")}>
            <dl className="grid gap-4 sm:grid-cols-2">
              <FieldRow
                label={t("contracts.extracted.noticePeriod")}
                leaf={fields.termination?.notice_period_days}
                path="termination.notice_period_days"
                needsConfirmationPaths={needsConfirmationPaths}
              />
              <FieldRow
                label={t("contracts.extracted.forConvenience")}
                leaf={fields.termination?.termination_for_convenience}
                path="termination.termination_for_convenience"
                needsConfirmationPaths={needsConfirmationPaths}
              />
              <FieldRow
                label={t("contracts.extracted.forCause")}
                leaf={fields.termination?.termination_for_cause_conditions}
                path="termination.termination_for_cause_conditions"
                needsConfirmationPaths={needsConfirmationPaths}
              />
            </dl>
          </Card>
        )}

        {(fields.liability?.type || fields.liability?.cap) && (
          <Card title={t("contracts.extracted.liability")}>
            <dl className="grid gap-4 sm:grid-cols-2">
              <FieldRow
                label={t("contracts.extracted.liabilityType")}
                leaf={fields.liability?.type}
                path="liability.type"
                needsConfirmationPaths={needsConfirmationPaths}
              />
              <FieldRow
                label={t("contracts.extracted.liabilityCap")}
                leaf={fields.liability?.cap}
                path="liability.cap"
                needsConfirmationPaths={needsConfirmationPaths}
              />
            </dl>
          </Card>
        )}

        {(fields.privacy?.processes_personal_data || fields.privacy?.dpa_present) && (
          <Card title={t("contracts.extracted.privacy")}>
            <dl className="grid gap-4 sm:grid-cols-2">
              <FieldRow
                label={t("contracts.extracted.processesPersonalData")}
                leaf={fields.privacy?.processes_personal_data}
                path="privacy.processes_personal_data"
                needsConfirmationPaths={needsConfirmationPaths}
              />
              <FieldRow
                label={t("contracts.extracted.dpaPresent")}
                leaf={fields.privacy?.dpa_present}
                path="privacy.dpa_present"
                needsConfirmationPaths={needsConfirmationPaths}
              />
            </dl>
          </Card>
        )}
      </div>

      {parties.length > 0 && (
        <Card title={t("contracts.extracted.parties")}>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-xs uppercase tracking-wide text-foreground-muted">
                <tr>
                  <th className="py-1.5 pr-4 font-medium">{t("contracts.extracted.partyRole")}</th>
                  <th className="py-1.5 pr-4 font-medium">{t("contracts.extracted.partyName")}</th>
                  <th className="py-1.5 pr-4 font-medium">{t("contracts.extracted.partyTaxId")}</th>
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
                {t("contracts.extracted.extractionConfidence")}
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
        <Card title={t("contracts.extracted.obligations")}>
          <ul className="space-y-2">
            {obligations.map((leaf, index) => (
              <li key={index} className="flex flex-wrap items-center gap-2 text-sm">
                <span className="text-foreground">{formatPlainValue(leaf.value, i18n)}</span>
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
        <Card title={t("contracts.extracted.deadlines")}>
          <ul className="space-y-2">
            {deadlines.map((deadline, index) => (
              <li key={index} className="flex flex-wrap items-center gap-2 text-sm">
                <span className="text-foreground">{deadline.description}</span>
                {deadline.date && (
                  <>
                    <span className="text-foreground-muted">— {formatDate(deadline.date.value, locale)}</span>
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
        <Card title={t("contracts.extracted.additional")}>
          <div className="grid gap-4 sm:grid-cols-3">
            {guarantees.length > 0 && (
              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-foreground-muted">
                  {t("contracts.extracted.guarantees")}
                </p>
                <ul className="mt-1 space-y-1 text-sm text-foreground">
                  {guarantees.map((leaf, index) => (
                    <li key={index}>{formatPlainValue(leaf.value, i18n)}</li>
                  ))}
                </ul>
              </div>
            )}
            {penalties.length > 0 && (
              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-foreground-muted">
                  {t("contracts.extracted.penalties")}
                </p>
                <ul className="mt-1 space-y-1 text-sm text-foreground">
                  {penalties.map((leaf, index) => (
                    <li key={index}>{formatPlainValue(leaf.value, i18n)}</li>
                  ))}
                </ul>
              </div>
            )}
            {subprocessors.length > 0 && (
              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-foreground-muted">
                  {t("contracts.extracted.subprocessors")}
                </p>
                <ul className="mt-1 space-y-1 text-sm text-foreground">
                  {subprocessors.map((leaf, index) => (
                    <li key={index}>{formatPlainValue(leaf.value, i18n)}</li>
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
