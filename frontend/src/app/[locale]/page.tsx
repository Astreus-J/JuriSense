import type { Metadata } from "next";
import { notFound } from "next/navigation";
import LandingPage from "@/components/landing/LandingPage";
import { DEFAULT_LOCALE, LOCALES, getLandingContent, isLocale } from "@/lib/landing-content";

interface LocalizedLandingPageProps {
  // Next 16: `params` is a Promise.
  params: Promise<{ locale: string }>;
}

export function generateStaticParams() {
  return LOCALES.filter((locale) => locale !== DEFAULT_LOCALE).map((locale) => ({ locale }));
}

/**
 * The translated landing page routes (`/pt`, `/es`). English, the native/primary language,
 * is served unprefixed by `src/app/page.tsx` instead. Only the two translated locales are
 * valid here -- anything else (including a path that happens to collide with another
 * top-level route) falls through to `notFound()` rather than silently rendering English.
 */
export async function generateMetadata({ params }: LocalizedLandingPageProps): Promise<Metadata> {
  const { locale } = await params;
  if (!isLocale(locale) || locale === "en") return {};
  const { meta } = getLandingContent(locale);
  return { title: meta.title, description: meta.description };
}

export default async function LocalizedLandingPage({ params }: LocalizedLandingPageProps) {
  const { locale } = await params;
  if (!isLocale(locale) || locale === "en") notFound();

  return <LandingPage locale={locale} />;
}
