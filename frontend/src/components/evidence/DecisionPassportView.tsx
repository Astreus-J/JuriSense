import Link from "next/link";
import { ShieldCheck } from "lucide-react";

import { Alert } from "@/components/ui/Alert";
import { Badge } from "@/components/ui/Badge";
import { ComplianceStatusBadge, RuleOutcomeBadge, SeverityBadge } from "@/components/compliance/ComplianceStatusBadge";
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
      <SupplierSection passport={passport} />
      <ContractSection passport={passport} />
      <PoliciesAndRulesSection passport={passport} />
      <ExternalSourcesSection passport={passport} />
      <ReviewersSection passport={passport} />
      <VerificationSection passport={passport} />
    </div>
  );
}

function DecisionSummary({ passport }: { passport: DecisionPassport }) {
  return (
    <section className="flex flex-wrap items-center gap-x-6 gap-y-2 rounded-xl border border-border bg-surface p-4">
      <ComplianceStatusBadge status={passport.status} />
      <Badge tone={passport.lifecycle === "ACTIVE" ? "info" : "neutral"}>
        {passport.lifecycle === "ACTIVE" ? "Effective decision" : "Superseded"}
      </Badge>
      <span className="font-mono text-xs text-foreground-muted">{passport.decisionId}</span>
      <span className="text-sm text-foreground-muted">
        Decided {formatDateTime(passport.createdAt)}
      </span>
      <span className="text-sm text-foreground-muted">
        Valid until {formatDateTime(passport.validUntil)}
      </span>
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

function SupplierSection({ passport }: { passport: DecisionPassport }) {
  return (
    <section className="space-y-2">
      <h2 className="text-sm font-semibold text-foreground">Supplier</h2>
      <div className="rounded-xl border border-border bg-surface p-4">
        <Link
          href={`/suppliers/${passport.supplierId}`}
          className="text-sm font-medium text-foreground hover:underline"
        >
          {passport.supplierLegalName}
        </Link>
        <p className="mt-1 text-xs text-foreground-muted">Tax id: {passport.supplierTaxId}</p>
      </div>
    </section>
  );
}

function ContractSection({ passport }: { passport: DecisionPassport }) {
  return (
    <section className="space-y-2">
      <h2 className="text-sm font-semibold text-foreground">Contract</h2>
      <div className="space-y-3 rounded-xl border border-border bg-surface p-4">
        <div>
          <Link
            href={`/contracts/${passport.contractId}`}
            className="text-sm font-medium text-foreground hover:underline"
          >
            {passport.contractTitle}
          </Link>
          <p className="mt-1 text-xs text-foreground-muted">
            Version {passport.contractVersionNumber}
          </p>
        </div>

        <div className="space-y-1">
          <p className="text-xs font-medium text-foreground-muted">Document hashes</p>
          {passport.documents.map((document) => (
            <p key={document.documentId} className="font-mono text-xs text-foreground-muted">
              {document.contentHash} ({document.mimeType}, {document.sizeBytes} bytes)
            </p>
          ))}
        </div>

        {passport.aiExecution && (
          <div>
            <p className="text-xs font-medium text-foreground-muted">AI execution</p>
            <p className="text-xs text-foreground-muted">
              {passport.aiExecution.provider} / {passport.aiExecution.modelName} (prompt{" "}
              {passport.aiExecution.promptVersion})
              {passport.aiExecution.extractedAt &&
                ` — extracted ${formatDateTime(passport.aiExecution.extractedAt)}`}
            </p>
          </div>
        )}
      </div>
    </section>
  );
}

function PoliciesAndRulesSection({ passport }: { passport: DecisionPassport }) {
  return (
    <section className="space-y-3">
      <h2 className="text-sm font-semibold text-foreground">
        Policies evaluated ({passport.policyVersions.length})
      </h2>
      {passport.policyVersions.length === 0 ? (
        <EmptyNote>No published policy was pooled for this decision.</EmptyNote>
      ) : (
        <ul className="flex flex-wrap gap-2">
          {passport.policyVersions.map((version) => (
            <li key={version.policyVersionId}>
              <Badge tone="neutral">Policy version {version.versionNumber}</Badge>
            </li>
          ))}
        </ul>
      )}

      <h3 className="text-sm font-semibold text-foreground">
        Rules triggered ({passport.ruleEvaluations.length})
      </h3>
      {passport.ruleEvaluations.length === 0 ? (
        <EmptyNote>No rules were evaluated for this decision.</EmptyNote>
      ) : (
        <ul className="space-y-3">
          {passport.ruleEvaluations.map((rule) => (
            <li key={rule.ruleEvaluationId} className="rounded-xl border border-border bg-surface p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-xs font-semibold text-foreground-muted">
                    {rule.ruleKey}
                  </span>
                  <span className="text-sm font-semibold text-foreground">{rule.ruleName}</span>
                </div>
                <div className="flex items-center gap-2">
                  <SeverityBadge severity={rule.severity} />
                  <RuleOutcomeBadge outcome={rule.outcome} />
                </div>
              </div>
              <p className="mt-2 text-sm text-foreground-muted">{rule.rationale}</p>
              {rule.approverRole && (
                <p className="mt-1 text-xs font-medium text-foreground-muted">
                  Required approval from: {rule.approverRole}
                </p>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function ExternalSourcesSection({ passport }: { passport: DecisionPassport }) {
  return (
    <section className="space-y-2">
      <h2 className="text-sm font-semibold text-foreground">External sources consulted</h2>
      {passport.externalSourcesConsulted.length === 0 ? (
        <EmptyNote>No external source was consulted for this decision.</EmptyNote>
      ) : (
        <ul className="flex flex-wrap gap-2">
          {passport.externalSourcesConsulted.map((source) => (
            <li key={source}>
              <Badge tone="neutral">{source}</Badge>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function ReviewersSection({ passport }: { passport: DecisionPassport }) {
  return (
    <section className="space-y-2">
      <h2 className="text-sm font-semibold text-foreground">
        Human reviewers ({passport.reviewers.length})
      </h2>
      {passport.reviewers.length === 0 ? (
        <EmptyNote>
          No human approval step was required — the decision was reached automatically.
        </EmptyNote>
      ) : (
        <ul className="space-y-2">
          {passport.reviewers.map((reviewer) => (
            <li
              key={reviewer.approvalRequestId}
              className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-xl border border-border bg-surface p-4 text-sm"
            >
              <span className="font-medium text-foreground">Step {reviewer.stepNumber}</span>
              <span className="text-foreground-muted">{reviewer.approverRole}</span>
              <Badge tone={reviewer.status === "approved" ? "success" : "neutral"}>
                {reviewer.status}
              </Badge>
              {reviewer.resolvedAt && (
                <span className="text-xs text-foreground-muted">
                  Resolved {formatDateTime(reviewer.resolvedAt)}
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function VerificationSection({ passport }: { passport: DecisionPassport }) {
  return (
    <section className="space-y-2 rounded-xl border border-dashed border-border bg-surface-muted p-4">
      <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
        <ShieldCheck className="size-4" aria-hidden="true" />
        Evidence package
      </div>
      <p className="text-xs text-foreground-muted">
        {passport.evidenceCount} evidence item{passport.evidenceCount === 1 ? "" : "s"}, committed
        to this Merkle root:
      </p>
      <p className="break-all font-mono text-xs text-foreground-muted">{passport.merkleRoot}</p>
    </section>
  );
}

function EmptyNote({ children }: { children: string }) {
  return (
    <p className="rounded-xl border border-dashed border-border bg-surface px-6 py-8 text-center text-sm text-foreground-muted">
      {children}
    </p>
  );
}
