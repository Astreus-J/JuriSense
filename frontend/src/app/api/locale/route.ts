import { NextResponse } from "next/server";

import {
  LOCALE_COOKIE,
  LOCALE_COOKIE_MAX_AGE_SECONDS,
  isAvailableLocale,
  isLocale,
} from "@/lib/i18n/config";

/**
 * Persists the user's language choice in the `NEXT_LOCALE` cookie. The app's routes are not
 * locale-prefixed, so this cookie is the single source of truth read by `getLocale()`; the
 * caller (`LocaleSwitcher`) follows up with `router.refresh()` so Server Components re-render
 * in the new language. Not a secret: not httpOnly, `SameSite=Lax`, one year. Cross-site POSTs
 * are already rejected for every `/api/*` route by `src/proxy.ts`.

 * A registered locale without a catalog is rejected (`isAvailableLocale`).
 */
export async function POST(request: Request): Promise<Response> {
  const body = (await request.json().catch(() => null)) as { locale?: unknown } | null;
  const locale = body?.locale;

  if (!isLocale(locale)) {
    return NextResponse.json({ detail: "Unknown language." }, { status: 400 });
  }
  if (!isAvailableLocale(locale)) {
    return NextResponse.json({ detail: "This language is not available yet." }, { status: 400 });
  }

  const response = new NextResponse(null, { status: 204 });
  response.cookies.set(LOCALE_COOKIE, locale, {
    path: "/",
    maxAge: LOCALE_COOKIE_MAX_AGE_SECONDS,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
  });
  return response;
}
