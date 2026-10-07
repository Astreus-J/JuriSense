import { AlertTriangle, CheckCircle2, Clock, SearchX } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { Badge } from "@/components/ui/Badge";
import type { BadgeTone } from "@/components/ui/Badge";
import { formatDateTime } from "@/lib/format";
import type { PublicVerificationResult, VerificationStatus } from "@/lib/evidence/types";

/**
 * FEATURE-8.3 (`docs/06-blockchain/verification.md` step 5): the three outcomes the doc
 * names, plus `pending` (this product's own addition for a submission whose underlying
 * network hasn't finalized yet). Never color-only (persona: "status is never color-only") --
 * every tone pairs with an icon and a plain-language label.
 */
const STATUS_CONFIG: Record<
  VerificationStatus,
  { tone: BadgeTone; icon: LucideIcon; label: string }
> = {
  verified: { tone: "success", icon: CheckCircle2, label: "Verified" },
  mismatch: { tone: "danger", icon: AlertTriangle, label: "Mismatch" },
  pending: { tone: "info", icon: Clock, label: "Pending" },
  not_found: { tone: "neutral", icon: SearchX, label: "Not found" },
};

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
  const { tone, icon: Icon, label } = STATUS_CONFIG[result.status];

  return (
    <div className="space-y-4 rounded-xl border border-border bg-surface p-6">
      <Badge tone={tone} icon={<Icon className="size-4" aria-hidden="true" />}>
        {label}
      </Badge>

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
