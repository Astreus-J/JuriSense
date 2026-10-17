import { DecisionMark, StatusBadge, statusTone } from "@/components/shared/StatusBadge";
import Link from "next/link";
import { ShieldCheck } from "lucide-react";

import { Alert } from "@/components/ui/Alert";
import { Badge, TONE_RAIL_CLASSES } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { cn } from "@/lib/cn";
import { formatDateTime } from "@/lib/format";
import type { DecisionPassport } from "@/lib/evidence/types";

/**
 * STORY-7.3.1: "a complete, reproducible 'why was this approved?' narrative for any
 * Decision, months or years later" — every field the acceptance criteria names, each
 * backed by an immutable record (`docs/03-domain/evidence.md`), in one read-only screen.
 * A Server Component: this view has no interactive state of its own, matching
 * `ComplianceReviewResults.tsx`'s "no client JS needed" precedent.
 */
export function DecisionPassportView({ passport }: { passport: DecisionPassport }) {
  return (
    <div className="space-y-8">
      <DecisionSummary passport={passport} />
      {passport.overridden && <OverrideNotice passport={passport} />}
      <PoliciesAndRulesSection passport={passport} />
      <div className="grid gap-x-10 gap-y-8 lg:grid-cols-2">
        <SubjectSection passport={passport} />
        <VerificationSection passport={passport} />
      </div>
      <ReviewersSection passport={passport} />
      <ExternalSourcesSection passport={passport} />
    </div>
  );
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
function DecisionSummary({ passport }: { passport: DecisionPassport }) {
  return (
    <section
      aria-label="Decision"
      className="flex flex-wrap items-center justify-between gap-x-8 gap-y-4 border-b border-border pb-5"
    >
      <div className="flex flex-wrap items-center gap-4">
        <DecisionMark value={passport.status} caption="Decision" />
        <Badge tone={passport.lifecycle === "ACTIVE" ? "info" : "neutral"}>
          {passport.lifecycle === "ACTIVE" ? "Effective decision" : "Superseded"}
        </Badge>
      </div>
      <dl className="grid grid-cols-2 gap-x-8 gap-y-2 sm:grid-cols-3">
        <Fact label="Decided">
          <span className="tabular-nums">{formatDateTime(passport.createdAt)}</span>
        </Fact>
        <Fact label="Valid until">
          <span className="tabular-nums">{formatDateTime(passport.validUntil)}</span>
        </Fact>
        <Fact label="Decision id">
          <span className="break-all font-mono text-xs">{passport.decisionId}</span>
        </Fact>
      </dl>
    </section>
  );
}

function OverrideNotice({ passport }: { passport: DecisionPassport }) {
  return (
    <Alert tone="warning" title="This decision was manually overridden">
      {passport.overrideJustification ?? "No justification was recorded."}
    </Alert>
  );
}

function SubjectSection({ passport }: { passport: DecisionPassport }) {
  return (
    <Section title="Supplier and contract">
      <dl className="space-y-3 border-t border-border pt-3">
        <Fact label="Supplier">
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
        <Fact label="Contract">
          <Link
            href={`/contracts/${passport.contractId}`}
            className="font-medium hover:underline"
          >
            {passport.contractTitle}
          </Link>
          <span className="ml-2 text-xs text-foreground-muted">
            Version {passport.contractVersionNumber}
          </span>
        </Fact>
        <Fact label="Document hashes">
          <ul className="space-y-0.5">
            {passport.documents.map((document) => (
              <li key={document.documentId} className="break-all font-mono text-xs text-foreground-muted">
                {document.contentHash}{" "}
                <span className="font-sans">
                  ({document.mimeType}, {new Intl.NumberFormat().format(document.sizeBytes)} bytes)
                </span>
              </li>
            ))}
          </ul>
        </Fact>
        {passport.aiExecution && (
          <Fact label="AI extraction">
            <span className="text-foreground-muted">
              {passport.aiExecution.provider} / {passport.aiExecution.modelName} (prompt{" "}
              {passport.aiExecution.promptVersion})
              {passport.aiExecution.extractedAt &&
                `, extracted ${formatDateTime(passport.aiExecution.extractedAt)}`}
            </span>
          </Fact>
        )}
      </dl>
    </Section>
  );
}

function PoliciesAndRulesSection({ passport }: { passport: DecisionPassport }) {
  return (
    <Section title={`Rules evaluated (${passport.ruleEvaluations.length})`}>
      <div className="flex flex-wrap items-center gap-2 text-xs text-foreground-muted">
        <span>Policies evaluated:</span>
        {passport.policyVersions.length === 0 ? (
          <span>no published policy was pooled for this decision.</span>
        ) : (
          passport.policyVersions.map((version) => (
            <Badge key={version.policyVersionId} tone="neutral">
              Policy version {version.versionNumber}
            </Badge>
          ))
        )}
      </div>

      {passport.ruleEvaluations.length === 0 ? (
        <EmptyState
          title="No rules evaluated"
          description="No rules were evaluated for this decision."
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
                    Required approval from{" "}
                    <span className="font-medium text-foreground">{rule.approverRole}</span>
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

function ExternalSourcesSection({ passport }: { passport: DecisionPassport }) {
  return (
    <Section title="External sources consulted">
      {passport.externalSourcesConsulted.length === 0 ? (
        <p className="text-sm text-foreground-muted">
          No external source was consulted for this decision.
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

function ReviewersSection({ passport }: { passport: DecisionPassport }) {
  return (
    <Section title={`Human reviewers (${passport.reviewers.length})`}>
      {passport.reviewers.length === 0 ? (
        <p className="text-sm text-foreground-muted">
          No human approval step was required; the decision was reached automatically.
        </p>
      ) : (
        <ul className="divide-y divide-border border-y border-border">
          {passport.reviewers.map((reviewer) => (
            <li
              key={reviewer.approvalRequestId}
              className="flex flex-wrap items-center gap-x-4 gap-y-1 py-2 text-sm"
            >
              <span className="font-medium text-foreground">Step {reviewer.stepNumber}</span>
              <span className="text-foreground-muted">{reviewer.approverRole}</span>
              {isApprovalStatus(reviewer.status) ? (
                <StatusBadge kind="approvalRequest" value={reviewer.status} />
              ) : (
                <Badge tone="neutral">{reviewer.status}</Badge>
              )}
              {reviewer.resolvedAt && (
                <span className="text-xs tabular-nums text-foreground-muted">
                  Resolved {formatDateTime(reviewer.resolvedAt)}
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
    </Section>
  );
}

function VerificationSection({ passport }: { passport: DecisionPassport }) {
  return (
    <Section title="Evidence package">
      <div className="space-y-2 border-t border-border pt-3">
        <p className="flex items-center gap-2 text-sm text-foreground">
          <ShieldCheck className="size-4 text-foreground-muted" aria-hidden="true" />
          <span className="tabular-nums">{passport.evidenceCount}</span> evidence item
          {passport.evidenceCount === 1 ? "" : "s"}, committed to this Merkle root
        </p>
        <p className="break-all rounded border border-border bg-surface-muted px-2.5 py-2 font-mono text-xs text-foreground-muted">
          {passport.merkleRoot}
        </p>
      </div>
    </Section>
  );
}
