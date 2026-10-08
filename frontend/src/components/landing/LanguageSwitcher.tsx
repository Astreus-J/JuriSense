import Link from "next/link";
import { LOCALES, LOCALE_LABELS, localeHref, type Locale } from "@/lib/landing-content";

export default function LanguageSwitcher({ locale }: { locale: Locale }) {
  return (
    <nav aria-label="Language" className="flex items-center gap-1 text-sm font-medium text-slate-500">
      {LOCALES.map((candidate, index) => (
        <span key={candidate} className="flex items-center">
          {index > 0 && <span className="mx-1 text-slate-300">/</span>}
          {candidate === locale ? (
            <span className="text-slate-900" aria-current="page" lang={candidate}>
              {candidate.toUpperCase()}
            </span>
          ) : (
            <Link
              href={localeHref(candidate)}
              className="rounded transition-colors hover:text-blue-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600"
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
