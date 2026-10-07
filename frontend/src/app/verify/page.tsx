import type { Metadata } from "next";

import { Brand } from "@/components/app-shell/Brand";
import { Button } from "@/components/ui/Button";
import { VerificationResultCard } from "@/components/verify/VerificationResultCard";
import { ApiError, verifyPublicReference } from "@/lib/evidence/backend";
import type { PublicVerificationResult } from "@/lib/evidence/types";

export const metadata: Metadata = {
  title: "Verify a decision — JuriSense Gate",
  description: "Independently verify a JuriSense Gate decision's anchored evidence hash.",
};

interface VerifyPageProps {
  // Next 16: `searchParams` is a Promise.
  searchParams: Promise<{ ref?: string }>;
}

/**
 * FEATURE-8.3 / STORY-8.3.1 (`docs/06-blockchain/verification.md`): the public,
 * unauthenticated verification page. No login, no organization context, no client-side
 * JavaScript required at all -- the reference lookup is a plain HTML `GET` form, so the
 * result lives at a shareable, bookmarkable URL (`/verify?ref=...`, the same shape a QR code
 * on an exported Decision Passport would encode) and works even if the visitor's browser
 * never runs the page's JS (persona: "prefer native platform capabilities when possible",
 * `ComplianceReviewResults.tsx`'s identical rationale for its own `<details>` disclosure).
 */
export default async function VerifyPage({ searchParams }: VerifyPageProps) {
  const { ref } = await searchParams;
  const trimmedRef = ref?.trim();
  const result = trimmedRef ? await lookUp(trimmedRef) : null;

  return (
    <div className="flex min-h-screen justify-center bg-surface-muted px-4 py-12">
      <div className="w-full max-w-md space-y-6">
        <Brand className="justify-center" />

        <div className="rounded-xl border border-border bg-surface p-6 shadow-sm">
          <div className="mb-6 space-y-1 text-center">
            <h1 className="text-xl font-semibold text-foreground">Verify a decision</h1>
            <p className="text-sm text-foreground-muted">
              Paste a Decision id or an evidence hash to independently check whether it was
              anchored.
            </p>
          </div>

          <form method="GET" className="flex flex-col gap-3 sm:flex-row sm:items-end">
            <div className="flex-1 space-y-1.5">
              <label htmlFor="ref" className="block text-sm font-medium text-foreground">
                Decision id or evidence hash
              </label>
              <input
                id="ref"
                name="ref"
                type="text"
                maxLength={255}
                defaultValue={trimmedRef ?? ""}
                placeholder="e.g. 3fa85f64-5717-4562-b3fc-2c963f66afa6"
                className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground shadow-sm placeholder:text-foreground-muted focus:outline-none focus:ring-2 focus:ring-focus-ring focus:border-transparent"
              />
            </div>
            <Button type="submit">Verify</Button>
          </form>
        </div>

        {result && <VerificationResultCard result={result} />}

        <p className="text-center text-xs text-foreground-muted">
          This check does not require a JuriSense account and does not reveal anything about
          the organization, supplier, or contract behind this decision.
        </p>
      </div>
    </div>
  );
}

/**
 * Wraps `verifyPublicReference` so a reference the backend itself rejects outright (over its
 * 255-char limit, or otherwise malformed enough to fail FastAPI's own query validation) still
 * renders this page's own "not found" state instead of throwing into an unhandled error for
 * an anonymous visitor -- the one case `verifyPublicReference`'s "never throws for an unknown
 * reference" contract doesn't itself cover, since that failure happens before the route body
 * ever runs.
 */
async function lookUp(reference: string): Promise<PublicVerificationResult> {
  try {
    return await verifyPublicReference(reference);
  } catch (error) {
    if (error instanceof ApiError) {
      return { status: "not_found", evidenceHash: null, provider: null, confirmedAt: null, referenceUrl: null };
    }
    throw error;
  }
}
