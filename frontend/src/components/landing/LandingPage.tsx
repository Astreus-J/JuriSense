import { getLandingContent, type Locale } from "@/lib/landing-content";
import Header from "./Header";
import Hero from "./Hero";
import Features from "./Features";
import HowItWorks from "./HowItWorks";
import Plans from "./Plans";
import Faq from "./Faq";
import CtaSection from "./CtaSection";
import Footer from "./Footer";

/**
 * The marketing landing page, shared by the native-English root route (`/`) and the
 * translated routes (`/pt`, `/es` — see `src/app/[locale]/page.tsx`). Scoped deliberately
 * to this subtree only: the authenticated app (`/login`, `/(app)/*`, `/verify`,
 * `/invite/accept`) stays English-only and outside any locale routing.
 */
export default function LandingPage({ locale }: { locale: Locale }) {
  const content = getLandingContent(locale);

  return (
    <div lang={locale !== "en" ? locale : undefined} className="bg-landing-canvas text-slate-900">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[100] focus:rounded-md focus:bg-blue-600 focus:px-4 focus:py-2 focus:text-sm focus:font-semibold focus:text-white"
      >
        {content.nav.skipToContent}
      </a>
      <Header content={content} locale={locale} />
      <main id="main-content">
        <Hero content={content} />
        <Features content={content} />
        <HowItWorks content={content} />
        <Plans content={content} />
        <Faq content={content} />
        <CtaSection content={content} />
      </main>
      <Footer content={content} />
    </div>
  );
}
