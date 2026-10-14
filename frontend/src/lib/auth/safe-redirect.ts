/**
 * Shared between `src/app/login/page.tsx` (the real, post-render redirect for an
 * already-authenticated visitor) and `src/proxy.ts` (the optimistic, pre-render one,
 * #132) -- both must agree on what counts as a safe `next` target, since `proxy.ts`
 * runs first and can short-circuit the page entirely. Keeping one implementation
 * avoids the two drifting apart into two different open-redirect bars.
 */
export function isSafeNextPath(next: string | undefined | null): next is string {
  if (typeof next !== "string" || next.length === 0) return false;
  if (next[0] !== "/") return false;
  // A single leading "/" is required, but a *second* "/" or a "\" right
  // after it produces a scheme-relative URL once a browser normalizes it
  // (both "//evil.com" and "/\evil.com" resolve to https://evil.com) --
  // reject both, plus any embedded backslash anywhere as defense in depth
  // (found in security review: the original check only rejected "//").
  if (/^\/[/\\]/.test(next) || next.includes("\\")) return false;
  return true;
}
