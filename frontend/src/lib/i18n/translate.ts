import { INTL_LOCALES } from "./config";
import type { Locale } from "./config";
import type { Messages } from "./messages/en";

type Paths<T, Prefix extends string = ""> = {
  [K in keyof T & string]: T[K] extends string ? `${Prefix}${K}` : Paths<T[K], `${Prefix}${K}.`>;
}[keyof T & string];

/** Every dotted key of the English catalog, e.g. `"suppliers.list.title"`. */
export type MessageKey = Paths<Messages>;

export type MessageParams = Record<string, string | number>;

export interface Translator {
  locale: Locale;
  /** Looks up `key` and replaces each `{param}` placeholder. */
  t(key: MessageKey, params?: MessageParams): string;
  /**
   * Picks a plural form. A plural message holds its forms separated by `|`, singular first:
   * `"{count} supplier | {count} suppliers"`. The form is chosen with `Intl.PluralRules` for
   * the active locale (`one` -> first form, everything else -> last), and `{count}` is
   * available as a placeholder alongside any extra `params`.
   */
  plural(key: MessageKey, count: number, params?: MessageParams): string;
}

function lookup(messages: Messages, key: string): string | undefined {
  let node: unknown = messages;
  for (const part of key.split(".")) {
    if (typeof node !== "object" || node === null) return undefined;
    node = (node as Record<string, unknown>)[part];
  }
  return typeof node === "string" ? node : undefined;
}

function interpolate(template: string, params?: MessageParams): string {
  if (!params) return template;
  return template.replace(/\{(\w+)\}/g, (placeholder, name: string) =>
    name in params ? String(params[name]) : placeholder,
  );
}

/** Pure (no `next/headers`), so it runs on the server and, with the active catalog, in the browser. */
export function createTranslator(locale: Locale, messages: Messages): Translator {
  const rules = new Intl.PluralRules(INTL_LOCALES[locale]);

  function t(key: MessageKey, params?: MessageParams): string {
    // A missing key cannot happen for typed callers (pt.ts is checked against en.ts); fall
    // back to the key itself so a bad dynamic lookup is visible instead of blank.
    return interpolate(lookup(messages, key) ?? key, params);
  }

  function plural(key: MessageKey, count: number, params?: MessageParams): string {
    const forms = (lookup(messages, key) ?? key).split("|").map((form) => form.trim());
    const form = rules.select(count) === "one" ? forms[0] : (forms[forms.length - 1] ?? forms[0]);
    return interpolate(form, { count, ...params });
  }

  return { locale, t, plural };
}
