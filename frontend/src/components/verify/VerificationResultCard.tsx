import { StatusBadge } from "@/components/shared/StatusBadge";
import { formatDateTime } from "@/lib/format";
import type { PublicVerificationResult } from "@/lib/evidence/types";

/**
 * Non-negotiable per `docs/09-planning/risks.md` risk 4: a `transparency_log` provider must
 * always read as a labeled fallback, never as a blockchain anchor. This is the one place the
 * public verification page renders `provider`, so it is the one place this labeling has to
 * hold.
 */
function providerLabel(provider: string): string {
  if (provider === "transparency_log") {
    return "a signed transparency log (fallback verification, not a blockchain anchor)";
  }
  if (provider === "constellation_digital_evidence") {
    return "Constellation Network";
  }
  return provider;
}

export function VerificationResultCard({ result }: { result: PublicVerificationResult }) {
  // FEATURE-8.3: verified / mismatch / not_found, plus this product's own `pending`; never
  // color-only -- the shared `verification` status map pairs each with an icon and a label.
  return (
    <div className="space-y-4 rounded-lg border border-border bg-surface p-6" role="status">
      <StatusBadge kind="verification" value={result.status} />

      <p className="text-sm text-foreground-muted">{resultMessage(result)}</p>

      {result.evidenceHash && (
        <div>
          <p className="text-xs font-medium text-foreground-muted">Evidence hash</p>
          <p className="break-all font-mono text-xs text-foreground">{result.evidenceHash}</p>
        </div>
      )}

      {result.provider && (
        <p className="text-xs text-foreground-muted">
          Anchored via {providerLabel(result.provider)}
          {result.confirmedAt && <> on {formatDateTime(result.confirmedAt)}</>}.
        </p>
      )}

      {result.referenceUrl && (
        <a
          href={result.referenceUrl}
          target="_blank"
          rel="noreferrer"
          className="inline-block text-xs font-medium text-primary hover:underline"
        >
          Check independently →
        </a>
      )}
    </div>
  );
}

function resultMessage(result: PublicVerificationResult): string {
  switch (result.status) {
    case "verified":
      return "This exact evidence hash was anchored at the time shown below, on a network JuriSense does not control.";
    case "mismatch":
      return "An anchor exists for this reference, but the hash on file no longer matches what was anchored. This is a tamper signal: treat this evidence as unverified.";
    case "pending":
      return "This evidence was submitted for anchoring, but the underlying network has not finalized it yet. Check back shortly.";
    case "not_found":
      return "No anchor was found for this reference. Check for a typo, or this may predate the Trust Layer being enabled.";
  }
}
