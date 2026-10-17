import { DecisionMark, StatusBadge } from "@/components/shared/StatusBadge";
import { statusTone } from "@/components/shared/status-map";
import Link from "next/link";
import { ShieldCheck } from "lucide-react";

import { Alert } from "@/components/ui/Alert";
import { Badge, TONE_RAIL_CLASSES } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { cn } from "@/lib/cn";
import { isRole } from "@/lib/auth/types";
import { formatDateTime } from "@/lib/format";
import { INTL_LOCALES } from "@/lib/i18n/config";
import { getI18n } from "@/lib/i18n/server";
import type { Translator } from "@/lib/i18n/translate";
import type { DecisionPassport } from "@/lib/evidence/types";

/**
 * STORY-7.3.1: "a complete, reproducible 'why was this approved?' narrative for any
 * Decision, months or years later" — every field the acceptance criteria names, each
 * backed by an immutable record (`docs/03-domain/evidence.md`), in one read-only screen.
 * A Server Component: this view has no interactive state of its own, matching
 * `ComplianceReviewResults.tsx`'s "no client JS needed" precedent.
 */
export async function DecisionPassportView({ passport }: { passport: DecisionPassport }) {
  const i18n = await getI18n();
  return (
    <div className="space-y-8">
      <DecisionSummary passport={passport} i18n={i18n} />
      {passport.overridden && <OverrideNotice passport={passport} i18n={i18n} />}
      <PoliciesAndRulesSection passport={passport} i18n={i18n} />
      <div className="grid gap-x-10 gap-y-8 lg:grid-cols-2">
        <SubjectSection passport={passport} i18n={i18n} />
        <VerificationSection passport={passport} i18n={i18n} />
      </div>
      <ReviewersSection passport={passport} i18n={i18n} />
      <ExternalSourcesSection passport={passport} i18n={i18n} />
    </div>
  );
}

interface SectionProps {
  passport: DecisionPassport;
  i18n: Translator;
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-3">
      <h2 className="text-base font-semibold text-foreground">{title}</h2>
      {children}
    </section>
  );
}

function Fact({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className="text-xs text-foreground-muted">{label}</dt>
      <dd className="mt-0.5 text-sm text-foreground">{children}</dd>
    </div>
  );
}

/** The decision is the page's answer, so it leads: outcome first, then when / until when / which record. */
function DecisionSummary({ passport, i18n: { t, locale } }: SectionProps) {
  return (
    <section
      aria-label={t("decisions.view.decision")}
      className="flex flex-wrap items-center justify-between gap-x-8 gap-y-4 border-b border-border pb-5"
    >
      <div className="flex flex-wrap items-center gap-4">
        <DecisionMark value={passport.status} caption={t("decisions.view.decision")} />
        <Badge tone={passport.lifecycle === "ACTIVE" ? "info" : "neutral"}>
          {passport.lifecycle === "ACTIVE" ? t("decisions.view.effective") : t("decisions.view.superseded")}
        </Badge>
      </div>
      <dl className="grid grid-cols-2 gap-x-8 gap-y-2 sm:grid-cols-3">
        <Fact label={t("decisions.view.decided")}>
          <span className="tabular-nums">{formatDateTime(passport.createdAt, locale)}</span>
        </Fact>
        <Fact label={t("decisions.view.validUntil")}>
          <span className="tabular-nums">{formatDateTime(passport.validUntil, locale)}</span>
        </Fact>
        <Fact label={t("decisions.view.decisionId")}>
          <span className="break-all font-mono text-xs">{passport.decisionId}</span>
        </Fact>
      </dl>
    </section>
  );
}

function OverrideNotice({ passport, i18n: { t } }: SectionProps) {
  return (
    <Alert tone="warning" title={t("decisions.view.overrideTitle")}>
      {passport.overrideJustification ?? t("decisions.view.overrideNone")}
    </Alert>
  );
}

function SubjectSection({ passport, i18n: { t, locale } }: SectionProps) {
  return (
    <Section title={t("decisions.view.subjectTitle")}>
      <dl className="space-y-3 border-t border-border pt-3">
        <Fact label={t("decisions.view.supplier")}>
          <Link
            href={`/suppliers/${passport.supplierId}`}
            className="font-medium hover:underline"
          >
            {passport.supplierLegalName}
          </Link>
          <span className="ml-2 font-mono text-xs text-foreground-muted">
            {passport.supplierTaxId}
          </span>
        </Fact>
        <Fact label={t("decisions.view.contract")}>
          <Link
            href={`/contracts/${passport.contractId}`}
            className="font-medium hover:underline"
          >
            {passport.contractTitle}
          </Link>
          <span className="ml-2 text-xs text-foreground-muted">
            {t("decisions.view.version", { number: passport.contractVersionNumber })}
          </span>
        </Fact>
        <Fact label={t("decisions.view.documentHashes")}>
          <ul className="space-y-0.5">
            {passport.documents.map((document) => (
              <li key={document.documentId} className="break-all font-mono text-xs text-foreground-muted">
                {document.contentHash}{" "}
                <span className="font-sans">
                  {t("decisions.view.documentMeta", {
                    mime: document.mimeType,
                    size: new Intl.NumberFormat(INTL_LOCALES[locale]).format(document.sizeBytes),
                  })}
                </span>
              </li>
            ))}
          </ul>
        </Fact>
        {passport.aiExecution && (
          <Fact label={t("decisions.view.aiExtraction")}>
            <span className="text-foreground-muted">
              {t("decisions.view.aiExecution", {
                provider: passport.aiExecution.provider ?? "—",
                model: passport.aiExecution.modelName ?? "—",
                version: passport.aiExecution.promptVersion ?? "—",
              })}
              {passport.aiExecution.extractedAt &&
                t("decisions.view.aiExtractedAt", {
                  date: formatDateTime(passport.aiExecution.extractedAt, locale),
                })}
            </span>
          </Fact>
        )}
      </dl>
    </Section>
  );
}

function PoliciesAndRulesSection({ passport, i18n: { t } }: SectionProps) {
  return (
    <Section title={t("decisions.view.rulesEvaluated", { count: passport.ruleEvaluations.length })}>
      <div className="flex flex-wrap items-center gap-2 text-xs text-foreground-muted">
        <span>{t("decisions.view.policiesEvaluated")}</span>
        {passport.policyVersions.length === 0 ? (
          <span>{t("decisions.view.noPolicyPooled")}</span>
        ) : (
          passport.policyVersions.map((version) => (
            <Badge key={version.policyVersionId} tone="neutral">
              {t("decisions.view.policyVersion", { number: version.versionNumber })}
            </Badge>
          ))
        )}
      </div>

      {passport.ruleEvaluations.length === 0 ? (
        <EmptyState
          title={t("decisions.view.noRulesTitle")}
          description={t("decisions.view.noRulesBody")}
        />
      ) : (
        <ul className="space-y-4">
          {passport.ruleEvaluations.map((rule) => {
            const needsAttention = rule.outcome === "REVIEW" || rule.outcome === "BLOCK";
            return (
              <li
                key={rule.ruleEvaluationId}
                className={cn(
                  "border-l-2 py-1 pl-4",
                  needsAttention
                    ? TONE_RAIL_CLASSES[statusTone("ruleOutcome", rule.outcome)]
                    : "border-l-border",
                )}
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex min-w-0 flex-wrap items-baseline gap-x-2">
                    <span className="font-mono text-xs text-foreground-muted">{rule.ruleKey}</span>
                    <span className="text-sm font-semibold text-foreground">{rule.ruleName}</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <StatusBadge kind="severity" value={rule.severity} />
                    <StatusBadge kind="ruleOutcome" value={rule.outcome} />
                  </div>
                </div>
                <p className="mt-1 text-sm text-foreground-muted">{rule.rationale}</p>
                {rule.approverRole && (
                  <p className="mt-1 text-xs text-foreground-muted">
                    {t("decisions.view.requiredApproval")}{" "}
                    <span className="font-medium text-foreground">
                      {isRole(rule.approverRole) ? t(`role.${rule.approverRole}`) : rule.approverRole}
                    </span>
                  </p>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </Section>
  );
}

function ExternalSourcesSection({ passport, i18n: { t } }: SectionProps) {
  return (
    <Section title={t("decisions.view.externalSources")}>
      {passport.externalSourcesConsulted.length === 0 ? (
        <p className="text-sm text-foreground-muted">
          {t("decisions.view.noExternalSources")}
        </p>
      ) : (
        <ul className="flex flex-wrap gap-2">
          {passport.externalSourcesConsulted.map((source) => (
            <li key={source}>
              <Badge tone="neutral">{source}</Badge>
            </li>
          ))}
        </ul>
      )}
    </Section>
  );
}

function isApprovalStatus(value: string): value is "pending" | "approved" | "rejected" {
  return value === "pending" || value === "approved" || value === "rejected";
}

function ReviewersSection({ passport, i18n: { t, locale } }: SectionProps) {
  return (
    <Section title={t("decisions.view.reviewers", { count: passport.reviewers.length })}>
      {passport.reviewers.length === 0 ? (
        <p className="text-sm text-foreground-muted">
          {t("decisions.view.noReviewers")}
        </p>
      ) : (
        <ul className="divide-y divide-border border-y border-border">
          {passport.reviewers.map((reviewer) => (
            <li
              key={reviewer.approvalRequestId}
              className="flex flex-wrap items-center gap-x-4 gap-y-1 py-2 text-sm"
            >
              <span className="font-medium text-foreground">
                {t("decisions.view.step", { number: reviewer.stepNumber })}
              </span>
              <span className="text-foreground-muted">
                {isRole(reviewer.approverRole) ? t(`role.${reviewer.approverRole}`) : reviewer.approverRole}
              </span>
              {isApprovalStatus(reviewer.status) ? (
                <StatusBadge kind="approvalRequest" value={reviewer.status} />
              ) : (
                <Badge tone="neutral">{reviewer.status}</Badge>
              )}
              {reviewer.resolvedAt && (
                <span className="text-xs tabular-nums text-foreground-muted">
                  {t("decisions.view.resolved", { date: formatDateTime(reviewer.resolvedAt, locale) })}
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
    </Section>
  );
}

function VerificationSection({ passport, i18n: { t, plural } }: SectionProps) {
  return (
    <Section title={t("decisions.view.evidencePackage")}>
      <div className="space-y-2 border-t border-border pt-3">
        <p className="flex items-center gap-2 text-sm text-foreground">
          <ShieldCheck className="size-4 text-foreground-muted" aria-hidden="true" />
          <span className="tabular-nums">{passport.evidenceCount}</span>{" "}
          {plural("decisions.view.evidenceItems", passport.evidenceCount)}
        </p>
        <p className="break-all rounded border border-border bg-surface-muted px-2.5 py-2 font-mono text-xs text-foreground-muted">
          {passport.merkleRoot}
        </p>
      </div>
    </Section>
  );
}
