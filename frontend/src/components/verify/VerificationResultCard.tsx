import { StatusBadge } from "@/components/shared/StatusBadge";
import { formatDateTime } from "@/lib/format";
import { getI18n } from "@/lib/i18n/server";
import type { Translator } from "@/lib/i18n/translate";
import type { PublicVerificationResult } from "@/lib/evidence/types";

/**
 * Non-negotiable per `docs/09-planning/risks.md` risk 4: a `transparency_log` provider must
 * always read as a labeled fallback, never as a blockchain anchor. This is the one place the
 * public verification page renders `provider`, so it is the one place this labeling has to
 * hold.
 */
function providerLabel(provider: string, { t }: Translator): string {
  if (provider === "transparency_log") {
    return t("verify.providerTransparencyLog");
  }
  if (provider === "constellation_digital_evidence") {
    return t("verify.providerConstellation");
  }
  return provider;
}

export async function VerificationResultCard({ result }: { result: PublicVerificationResult }) {
  const i18n = await getI18n();
  const { t, locale } = i18n;
  // FEATURE-8.3: verified / mismatch / not_found, plus this product's own `pending`; never
  // color-only -- the shared `verification` status map pairs each with an icon and a label.
  return (
    <div className="space-y-4 rounded-lg border border-border bg-surface p-6" role="status">
      <StatusBadge kind="verification" value={result.status} />

      <p className="text-sm text-foreground-muted">{t(`verify.${result.status}`)}</p>

      {result.evidenceHash && (
        <div>
          <p className="text-xs font-medium text-foreground-muted">{t("verify.evidenceHash")}</p>
          <p className="break-all font-mono text-xs text-foreground">{result.evidenceHash}</p>
        </div>
      )}

      {result.provider && (
        <p className="text-xs text-foreground-muted">
          {result.confirmedAt
            ? t("verify.anchoredViaOn", {
                provider: providerLabel(result.provider, i18n),
                date: formatDateTime(result.confirmedAt, locale),
              })
            : t("verify.anchoredVia", { provider: providerLabel(result.provider, i18n) })}
        </p>
      )}

      {result.referenceUrl && (
        <a
          href={result.referenceUrl}
          target="_blank"
          rel="noreferrer"
          className="inline-block text-xs font-medium text-primary hover:underline"
        >
          {t("verify.checkIndependently")}
        </a>
      )}
    </div>
  );
}
