/**
 * #129 (security/pentest QA round, 2026-09-28): the BFF pattern's session cookies
 * (`sameSite: "lax"`, httpOnly — see `cookie-config.ts`) already stop the classic CSRF
 * vector by themselves, since a browser never attaches a `lax` cookie to a cross-site
 * POST/PUT/PATCH/DELETE request (only to a cross-site top-level GET navigation) — and
 * every mutating route under `src/app/api/` is POST/PUT/PATCH/DELETE; none of the
 * handful of GET route handlers (`compliance/reviews`, `compliance/reviews/[id]`,
 * `users/invites`) change state, so there is no "state-changing GET" for that residual
 * `sameSite=lax` gap to matter against (confirmed by reading every `route.ts` in this
 * codebase, not assumed).
 *
 * This is a second, independent layer on top of that, not a replacement for it:
 * `sameSite` is the browser honoring a cookie attribute, which has historically had
 * implementation gaps and defaults this app has no control over if a user's browser is
 * old or misconfigured. Checking the request's own origin against this app's origin,
 * for every mutating request, is the standard complementary defense (OWASP's CSRF
 * Cheat Sheet, "Verifying Origin with Standard Headers") and doesn't depend on any
 * cookie attribute at all.
 *
 * Every mutation in this app is a `fetch()` call from this app's own client-side code
 * (confirmed: every `<form>` here uses `onSubmit` + `fetch`, never a native HTML
 * `action=`/`method=` submission) -- so a legitimate request always carries either
 * `Sec-Fetch-Site` (sent by every current evergreen browser for a `fetch`/XHR/form
 * submission) or, failing that, an `Origin` header (sent by `fetch`/XHR for any
 * non-GET/HEAD request, same-origin or not, per the Fetch spec). A request with
 * neither header is not something this BFF's own frontend would ever send, so it is
 * rejected rather than assumed safe -- fail closed, matching this codebase's existing
 * "deny by default" convention (ADR-012) rather than fail open on an unrecognized shape.
 *
 * Returns whether `request` should be rejected -- never throws, never builds a
 * Response itself, so the caller (`proxy.ts`) decides exactly how to respond.
 */
export function isCrossSiteMutation(request: Request): boolean {
  const SAFE_METHODS = new Set(["GET", "HEAD", "OPTIONS"]);
  if (SAFE_METHODS.has(request.method)) return false;

  const secFetchSite = request.headers.get("sec-fetch-site");
  if (secFetchSite !== null) {
    // "same-origin": a same-origin fetch/form. "none": not triggered by a webpage at
    // all (e.g. a typed URL, a bookmark, a browser extension acting on the user's own
    // behalf) -- not a cross-site forgery either way, since no attacker-controlled page
    // is involved. Anything else ("same-site", "cross-site") is rejected.
    return secFetchSite !== "same-origin" && secFetchSite !== "none";
  }

  const origin = request.headers.get("origin");
  if (origin === null) return true;

  // `request.url`'s host reflects the server's own bind address (e.g. `0.0.0.0`), not
  // the `Host` the browser actually requested -- found empirically (a legitimate
  // same-origin request was incorrectly rejected) while verifying this against the
  // standalone production server. `Host` is the right comparison target instead; only
  // the host:port matters here, not the scheme -- the production reverse proxy
  // terminates TLS and talks to this app over plain HTTP, so `Origin`'s scheme will
  // legitimately be `https` while the request itself arrives as `http`.
  //
  // Deliberately NOT `X-Forwarded-Host`: unlike `Host` (which Nginx's standard
  // `proxy_set_header Host $host;` reverse-proxy config -- the one this app's
  // deployment architecture, `docs/04-architecture/deployment.md`, calls for --
  // already carries as the browser's real target), `X-Forwarded-Host` has no
  // guarantee anywhere in this repo today that an intermediary overwrites rather than
  // passes through a client-supplied value (security review, 2026-10-12). Trusting it
  // would let a request with a forged `X-Forwarded-Host` match an attacker-controlled
  // `Origin` on exactly the clients this fallback exists to cover (no `Sec-Fetch-Site`
  // support). Revisit only alongside an explicit trusted-proxy allowlist if a future
  // deployment topology actually needs it.
  const host = request.headers.get("host");
  if (host === null) return true;

  try {
    return new URL(origin).host !== host;
  } catch {
    return true;
  }
}
