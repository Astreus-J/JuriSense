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
