/**
 * Locale-aware date/time formatting (persona: "Never manually concatenate currency/date
 * strings when standard formatting APIs exist"). `undefined` locale defers to the
 * runtime's/browser's own locale rather than hard-coding one.
 */
export function formatDateTime(iso: string): string {
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(
    new Date(iso),
  );
}

/** Date-only, locale-aware — for extracted contract dates (`duration.start_date`,
 * `deadlines[].date`, etc.), which carry no time component. */
export function formatDate(iso: string): string {
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(new Date(iso));
}

/**
 * Locale-aware currency formatting. Falls back to a plain number if `currency` isn't a
 * valid ISO 4217 code (`Intl.NumberFormat` throws on an invalid one, and AI-extracted
 * currency text is not guaranteed to be clean) — better to show the raw amount than crash
 * the field it's rendered in.
 */
export function formatCurrency(amount: number, currency?: string | null): string {
  if (!currency) return new Intl.NumberFormat(undefined).format(amount);
  try {
    return new Intl.NumberFormat(undefined, { style: "currency", currency }).format(amount);
  } catch {
    return `${new Intl.NumberFormat(undefined).format(amount)} ${currency}`;
  }
}

/** `0.973` -> `"97%"`. Confidence scores are a ratio, never money/a count — kept in its own
 * helper rather than reusing `Intl.NumberFormat`'s percent style ad hoc at every call site. */
export function formatConfidence(confidence: number): string {
  return new Intl.NumberFormat(undefined, { style: "percent", maximumFractionDigits: 0 }).format(
    confidence,
  );
}
