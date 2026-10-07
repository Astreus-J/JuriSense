import Link from "next/link";
import { LOCALES, LOCALE_LABELS, localeHref, type Locale } from "@/lib/landing-content";

export default function LanguageSwitcher({ locale }: { locale: Locale }) {
  return (
    <nav aria-label="Language" className="flex items-center gap-1 text-sm font-medium text-gray-500">
      {LOCALES.map((candidate, index) => (
        <span key={candidate} className="flex items-center">
          {index > 0 && <span className="mx-1 text-gray-300">/</span>}
          {candidate === locale ? (
            <span className="text-gray-900" aria-current="page" lang={candidate}>
              {candidate.toUpperCase()}
            </span>
          ) : (
            <Link
              href={localeHref(candidate)}
              className="hover:text-blue-600 transition-colors"
              title={LOCALE_LABELS[candidate]}
              hrefLang={candidate}
              lang={candidate}
            >
              {candidate.toUpperCase()}
            </Link>
          )}
        </span>
      ))}
    </nav>
  );
}
