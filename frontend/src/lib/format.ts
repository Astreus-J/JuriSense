import { INTL_LOCALES } from "@/lib/i18n/config";
import type { Locale } from "@/lib/i18n/config";

/**
 * Locale-aware date/time/number formatting (persona: "Never manually concatenate currency/date
 * strings when standard formatting APIs exist"). Every helper takes the active app `Locale`
 * (from `getI18n()` on the server or `useI18n()` in the browser) and maps it to a BCP 47 tag
 * (`en` -> en-US, `pt` -> pt-BR) rather than deferring to the runtime's own locale, so server
 * and client always render the same string for the same user choice.
 */
export function formatDateTime(iso: string, locale: Locale): string {
  return new Intl.DateTimeFormat(INTL_LOCALES[locale], { dateStyle: "medium", timeStyle: "short" }).format(
    new Date(iso),
  );
}

/** Date-only, locale-aware — for extracted contract dates (`duration.start_date`,
 * `deadlines[].date`, etc.), which carry no time component. */
export function formatDate(iso: string, locale: Locale): string {
  return new Intl.DateTimeFormat(INTL_LOCALES[locale], { dateStyle: "medium" }).format(new Date(iso));
}

/**
 * Locale-aware currency formatting. Falls back to a plain number if `currency` isn't a
 * valid ISO 4217 code (`Intl.NumberFormat` throws on an invalid one, and AI-extracted
 * currency text is not guaranteed to be clean) — better to show the raw amount than crash
 * the field it's rendered in.
 *
 * QA review (2026-09-30): `amount` is a nullable AI-extracted field
 * (`ExtractedValue.value` can legitimately be `null`) despite this function's earlier
 * `number`-only signature, which let `Intl.NumberFormat(...).format(null)` silently
 * coerce to `0` — misrepresenting "unknown/unconfirmed value" as "confirmed zero," and
 * disagreeing with every other field's "—" placeholder for the identical null case.
 */
export function formatCurrency(
  amount: number | null | undefined,
  locale: Locale,
  currency?: string | null,
): string {
  if (amount === null || amount === undefined) return "—";
  const tag = INTL_LOCALES[locale];
  if (!currency) return new Intl.NumberFormat(tag).format(amount);
  try {
    return new Intl.NumberFormat(tag, { style: "currency", currency }).format(amount);
  } catch {
    return `${new Intl.NumberFormat(tag).format(amount)} ${currency}`;
  }
}

/** `0.973` -> `"97%"`. Confidence scores are a ratio, never money/a count — kept in its own
 * helper rather than reusing `Intl.NumberFormat`'s percent style ad hoc at every call site. */
export function formatConfidence(confidence: number, locale: Locale): string {
  return new Intl.NumberFormat(INTL_LOCALES[locale], { style: "percent", maximumFractionDigits: 0 }).format(
    confidence,
  );
}
