import type { NextConfig } from "next";

const isProduction = process.env.NODE_ENV === "production";

/**
 * #128 (security/pentest QA round, 2026-09-28): no CSP or security response headers
 * were shipped before this. Written against this app's actual script/style sources
 * (confirmed by building and inspecting the rendered HTML, not guessed):
 *
 * - No external script, style, image, or font origin is ever loaded -- `next/font`
 *   self-hosts Geist at build time, Tailwind compiles to a local stylesheet (no
 *   CSS-in-JS), and every backend call happens server-side (Route Handlers / Proxy),
 *   never from browser JS. So every directive below is `'self'`-only, no third-party
 *   domain allowlist is needed anywhere.
 * - `script-src` needs `'unsafe-inline'`: Next.js's own RSC/hydration bootstrap emits
 *   inline `<script>` tags (confirmed in the built output) that a nonce-based policy
 *   could replace, but that would force every page -- including the two static
 *   marketing routes (`/`, `/pt`, `/es`; confirmed `○ (Static)` in the build output)
 *   -- into dynamic rendering for no real benefit here (there is no external/
 *   attacker-controlled script source for a nonce to guard against). Accepted,
 *   documented trade-off; revisit if a nonce ever becomes necessary for another
 *   reason.
 * - `style-src` does NOT need `'unsafe-inline'` -- confirmed zero inline `<style>`
 *   tags or `style={{...}}` props anywhere in this codebase.
 * - `frame-ancestors 'none'` + `object-src 'none'` + `base-uri 'self'` +
 *   `form-action 'self'` close the clickjacking/embedding and legacy-plugin/base-tag-
 *   hijack vectors `'unsafe-inline'` alone wouldn't.
 */
const cspHeader = `
  default-src 'self';
  script-src 'self' 'unsafe-inline';
  style-src 'self';
  img-src 'self' data:;
  font-src 'self';
  connect-src 'self';
  object-src 'none';
  base-uri 'self';
  form-action 'self';
  frame-ancestors 'none';
  ${isProduction ? "upgrade-insecure-requests;" : ""}
`
  .replace(/\s{2,}/g, " ")
  .trim();

const nextConfig: NextConfig = {
  // Standalone build: produces server.js with only the dependencies it needs, so the
  // Docker image doesn't need the full node_modules tree.
  output: "standalone",
  async headers() {
    return [
      {
        // Applies to every route, including /api/* -- these headers are cheap,
        // universal defense-in-depth that costs nothing on a JSON response.
        source: "/(.*)",
        headers: [
          { key: "Content-Security-Policy", value: cspHeader },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
          ...(isProduction
            ? [
                {
                  key: "Strict-Transport-Security",
                  value: "max-age=63072000; includeSubDomains; preload",
                },
              ]
            : []),
        ],
      },
    ];
  },
};

export default nextConfig;
