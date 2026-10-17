"use client";

import { createContext, useContext, useMemo } from "react";
import type { ReactNode } from "react";

import type { Locale } from "./config";
import type { Messages } from "./messages/en";
import { createTranslator } from "./translate";
import type { Translator } from "./translate";

const I18nContext = createContext<Translator | null>(null);

/**
 * Fed by the root layout with ONLY the active locale's catalog (never every language), so
 * Client Components can translate without a round trip. Server Components use `getI18n()`.
 */
export function I18nProvider({
  locale,
  messages,
  children,
}: {
  locale: Locale;
  messages: Messages;
  children: ReactNode;
}) {
  const translator = useMemo(() => createTranslator(locale, messages), [locale, messages]);
  return <I18nContext.Provider value={translator}>{children}</I18nContext.Provider>;
}

/** `const { t, plural, locale } = useI18n();` for Client Components. */
export function useI18n(): Translator {
  const translator = useContext(I18nContext);
  if (!translator) throw new Error("useI18n must be used inside <I18nProvider>.");
  return translator;
}
