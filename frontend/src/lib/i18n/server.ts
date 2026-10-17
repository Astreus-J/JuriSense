import "server-only";

import { cache } from "react";
import type { Metadata } from "next";
import { cookies, headers } from "next/headers";

import { getMessages } from "./catalog";
import { AVAILABLE_LOCALES, DEFAULT_LOCALE, LOCALE_COOKIE, PRODUCT_NAME, isAvailableLocale } from "./config";
import type { Locale } from "./config";
import { createTranslator } from "./translate";
import type { MessageKey, Translator } from "./translate";

/**
 * First available language in an `Accept-Language` header (`pt-BR,pt;q=0.9,en;q=0.8` -> `pt`),
 * honoring q-values. Only the primary subtag matters. Unavailable languages (e.g. `es` until its
 * catalog exists) are skipped; no match means the default locale.
 */
function negotiateLocale(acceptLanguage: string | null): Locale {
  if (!acceptLanguage) return DEFAULT_LOCALE;
  const candidates = acceptLanguage
    .split(",")
    .map((part, index) => {
      const [tag, ...params] = part.trim().split(";");
      const q = params.map((p) => p.trim()).find((p) => p.startsWith("q="));
      const weight = q ? Number.parseFloat(q.slice(2)) : 1;
      return { primary: tag.toLowerCase().split("-")[0], weight: Number.isNaN(weight) ? 0 : weight, index };
    })
    .filter((candidate) => candidate.weight > 0)
    .sort((a, b) => b.weight - a.weight || a.index - b.index);
  const match = candidates.find((candidate) =>
    (AVAILABLE_LOCALES as readonly string[]).includes(candidate.primary),
  );
  return match ? (match.primary as Locale) : DEFAULT_LOCALE;
}

/**
 * The active locale for this request: the `NEXT_LOCALE` cookie when it holds an available
 * locale, otherwise negotiated from `Accept-Language`, otherwise English. Deduped per request.
 */
export const getLocale = cache(async (): Promise<Locale> => {
  const stored = (await cookies()).get(LOCALE_COOKIE)?.value;
  if (isAvailableLocale(stored)) return stored;
  return negotiateLocale((await headers()).get("accept-language"));
});

/** Translator for Server Components: `const { t, plural, locale } = await getI18n();`. */
export const getI18n = cache(async (): Promise<Translator> => {
  const locale = await getLocale();
  return createTranslator(locale, getMessages(locale));
});

/** `export const generateMetadata = pageTitle("meta.suppliers");` -> "<title> — JuriSense Gate". */
export function pageTitle(key: MessageKey): () => Promise<Metadata> {
  return async () => {
    const { t } = await getI18n();
    return { title: `${t(key)} — ${PRODUCT_NAME}` };
  };
}
