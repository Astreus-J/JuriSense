"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { Globe } from "lucide-react";

import { compactControlClasses } from "@/components/ui/Field";
import { cn } from "@/lib/cn";
import { useI18n } from "@/lib/i18n/client";
import { AVAILABLE_LOCALES, LOCALE_NATIVE_NAMES, LOCALE_SHORT_LABELS, isLocale } from "@/lib/i18n/config";
import type { Locale } from "@/lib/i18n/config";

/**
 * Language picker for the top bar and the unauthenticated auth screens. A native `<select>`
 * on purpose: free keyboard/screen-reader behavior, consistent with the app's other selects,
 * and it shows the current language at a glance. Labels are abbreviated (EN / PT / ES); the
 * full native names live in aria-labels and tooltips.
 *
 * Choosing a language POSTs to `/api/locale` (which sets the `NEXT_LOCALE` cookie) and then
 * `router.refresh()`es so Server Components re-render in the new language.
 */
export function LocaleSwitcher({ className }: { className?: string }) {
  const router = useRouter();
  const { t, locale } = useI18n();
  const [pending, startTransition] = useTransition();
  const [failed, setFailed] = useState(false);

  async function handleChange(next: string) {
    if (!isLocale(next) || next === locale) return;
    setFailed(false);
    try {
      const response = await fetch("/api/locale", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ locale: next satisfies Locale }),
      });
      if (!response.ok) throw new Error(`Locale request failed with ${response.status}`);
      startTransition(() => router.refresh());
    } catch (error) {
      console.error("Could not change language", error);
      setFailed(true);
    }
  }

  return (
    <div className={cn("flex items-center gap-1.5", className)}>
      <Globe className="size-4 shrink-0 text-foreground-muted" aria-hidden="true" />
      <select
        aria-label={`${t("shell.language")}: ${LOCALE_NATIVE_NAMES[locale]}`}
        title={LOCALE_NATIVE_NAMES[locale]}
        value={locale}
        disabled={pending}
        onChange={(event) => void handleChange(event.target.value)}
        className={cn(compactControlClasses, "cursor-pointer")}
      >
        {AVAILABLE_LOCALES.map((candidate) => (
          <option
            key={candidate}
            value={candidate}
            lang={candidate}
            aria-label={LOCALE_NATIVE_NAMES[candidate]}
            title={LOCALE_NATIVE_NAMES[candidate]}
          >
            {LOCALE_SHORT_LABELS[candidate]}
          </option>
        ))}
      </select>
      {failed && (
        <span role="alert" className="text-xs text-danger">
          {t("shell.languageChangeFailed")}
        </span>
      )}
    </div>
  );
}
