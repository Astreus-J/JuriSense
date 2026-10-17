import { DEFAULT_LOCALE } from "./config";
import type { Locale } from "./config";
import { en } from "./messages/en";
import type { Messages } from "./messages/en";
import { es } from "./messages/es";
import { pt } from "./messages/pt";

/**
 * Registered catalogs; a locale missing here falls back to English.
 */
const CATALOGS: Partial<Record<Locale, Messages>> = { en, pt, es };

export function getMessages(locale: Locale): Messages {
  return CATALOGS[locale] ?? CATALOGS[DEFAULT_LOCALE] ?? en;
}
