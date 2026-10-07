import Image from "next/image";
import Link from "next/link";
import { contact, localeHref, type LandingContent, type Locale } from "@/lib/landing-content";
import LanguageSwitcher from "./LanguageSwitcher";

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
    <header className="sticky top-0 z-50 bg-white/90 backdrop-blur border-b border-gray-100">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 min-h-16 py-3 flex flex-wrap items-center justify-between gap-y-2 gap-x-4">
        <Link href={localeHref(locale)} className="flex items-center gap-2 shrink-0">
          <Image
            src="/img/logo.png"
            alt="JuriSense logo"
            width={36}
            height={36}
            className="rounded-lg"
          />
          <span className="text-xl font-bold text-gray-900">JuriSense</span>
        </Link>

        <nav className="hidden md:flex items-center gap-8 text-sm font-medium text-gray-600">
          {navLinks.map((link) => (
            <a key={link.href} href={link.href} className="hover:text-blue-600 transition-colors">
              {link.label}
            </a>
          ))}
        </nav>

        <div className="flex flex-wrap items-center justify-end gap-3 sm:gap-4">
          <LanguageSwitcher locale={locale} />
          <Link
            href="/login"
            className="hidden sm:inline-block text-sm font-medium text-gray-600 hover:text-blue-600 transition-colors"
          >
            {content.nav.login}
          </Link>
          <a
            href={contact.whatsapp}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 transition-colors"
          >
            {content.nav.talkToUs}
          </a>
        </div>
      </div>
    </header>
  );
}
