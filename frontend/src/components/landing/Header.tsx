import Image from "next/image";
import Link from "next/link";
import { contact, localeHref, type LandingContent, type Locale } from "@/lib/landing-content";
import { primaryButton } from "./buttonStyles";
import LanguageSwitcher from "./LanguageSwitcher";
import MobileMenu from "./MobileMenu";

export default function Header({
  content,
  locale,
}: {
  content: LandingContent;
  locale: Locale;
}) {
  const navLinks = [
    { href: "#features", label: content.nav.features },
    { href: "#how-it-works", label: content.nav.howItWorks },
    { href: "#pricing", label: content.nav.pricing },
    { href: "#faq", label: content.nav.faq },
  ];

  return (
    <header className="sticky top-0 z-50 border-b border-slate-200/80 bg-white/85 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
        {/* Wordmark deliberately distinguishes the platform brand ("JuriSense") from the
            product it carries ("Gate") — see docs/00-project/overview.md: "JuriSense is the
            company/platform brand. The first commercial product built on it is JuriSense
            Gate." A flat "JuriSense" wordmark alone would misstate that relationship. */}
        <Link href={localeHref(locale)} className="flex shrink-0 items-center gap-2.5">
          <Image src="/img/logo.png" alt="" width={32} height={32} className="rounded-lg" priority />
          <span className="text-lg font-bold tracking-tight text-slate-900">
            JuriSense <span className="font-medium text-slate-400">Gate</span>
          </span>
        </Link>

        {/* The full nav row (links + switcher + login + CTA) only fits comfortably from `lg`
            (1024px) up — at `md` (768px, tablet portrait) it visibly wrapped ("Log in" and the
            CTA label breaking onto two lines). Tablet keeps the same hamburger menu as mobile
            rather than a half-squeezed in-between layout. */}
        <nav aria-label={content.nav.primaryNav} className="hidden items-center gap-8 text-sm font-medium text-slate-600 lg:flex">
          {navLinks.map((link) => (
            <a key={link.href} href={link.href} className="transition-colors hover:text-blue-600">
              {link.label}
            </a>
          ))}
        </nav>

        <div className="flex items-center gap-3">
          <div className="hidden lg:block">
            <LanguageSwitcher locale={locale} />
          </div>
          <Link
            href="/login"
            className="hidden text-sm font-medium text-slate-600 transition-colors hover:text-blue-600 sm:inline-block"
          >
            {content.nav.login}
          </Link>
          {/* Wrapped (rather than passing "hidden" into primaryButton's own className) because
              the button's base style already sets `inline-flex` unconditionally — two
              unconditional, conflicting display utilities on the same element are a Tailwind
              ordering trap. Controlling visibility on a separate wrapper avoids it outright. */}
          <span className="hidden sm:inline-flex">
            <a href={contact.whatsapp} target="_blank" rel="noopener noreferrer" className={primaryButton("sm")}>
              {content.nav.talkToUs}
            </a>
          </span>
          <MobileMenu content={content} locale={locale} navLinks={navLinks} />
        </div>
      </div>
    </header>
  );
}
