/**
 * Locale configuration for the authenticated app, login/invite/verify pages and error pages.
 * Client-safe (no `next/headers`, no message catalogs) so Client Components can import it.
 *
 * The marketing landing page has its own URL-prefixed locale system
 * (`src/lib/landing-content.ts`, `/pt`, `/es`); the app routes are NOT locale-prefixed, so the
 * active locale lives in a cookie (see `server.ts` and `POST /api/locale`).
 *
 * `Locale` intentionally mirrors the landing page's `Locale` union so both systems speak the
 * same three language codes.
 */
export type Locale = "en" | "pt" | "es";

export const LOCALES: readonly Locale[] = ["en", "pt", "es"];
export const DEFAULT_LOCALE: Locale = "en";

/**
 * Locales that actually have a message catalog (all three today). A locale without a
 * catalog falls back to English in `catalog.ts`; add it here only once its `messages/<x>.ts`
 * exists.
 */
export const AVAILABLE_LOCALES: readonly Locale[] = ["en", "pt", "es"];

export const LOCALE_COOKIE = "NEXT_LOCALE";
export const LOCALE_COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 365;

/** Full names, always in their own language (aria-labels and tooltips). */
export const LOCALE_NATIVE_NAMES: Record<Locale, string> = {
  en: "English",
  pt: "Português (Brasil)",
  es: "Español",
};

/** Compact labels shown in the language switcher itself. */
export const LOCALE_SHORT_LABELS: Record<Locale, string> = {
  en: "EN",
  pt: "PT",
  es: "ES",
};

/** BCP 47 tag handed to `Intl.*` for dates, numbers, currency and plural rules. */
export const INTL_LOCALES: Record<Locale, string> = {
  en: "en-US",
  pt: "pt-BR",
  es: "es-419", // neutral Latin American Spanish
};

/** Value of `<html lang>` for each locale. */
export const HTML_LANG: Record<Locale, string> = {
  en: "en",
  pt: "pt-BR",
  es: "es",
};

/** Product name shown in page titles; a brand, deliberately never translated. */
export const PRODUCT_NAME = "JuriSense Gate";

export function isLocale(value: unknown): value is Locale {
  return typeof value === "string" && (LOCALES as readonly string[]).includes(value);
}

export function isAvailableLocale(value: unknown): value is Locale {
  return typeof value === "string" && (AVAILABLE_LOCALES as readonly string[]).includes(value);
}
