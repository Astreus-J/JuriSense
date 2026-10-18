"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Menu, X } from "lucide-react";
import { contact, type LandingContent, type Locale } from "@/lib/landing-content";
import { primaryButton, secondaryButton } from "./buttonStyles";
import LanguageSwitcher from "./LanguageSwitcher";

/**
 * Mobile navigation drawer for the marketing header. Mirrors the accessible interaction
 * pattern already established and audited for the authenticated app's own
 * `src/components/app-shell/MobileNav.tsx` (focus-to-close-button on open, Escape to close,
 * body-scroll lock, click-capture to close on link selection) rather than inventing a new one —
 * the landing page's "Features / How it works / Pricing / FAQ" nav links were previously
 * unreachable below the `md` breakpoint entirely, which this fixes.
 */
export default function MobileMenu({
  content,
  locale,
  navLinks,
}: {
  content: LandingContent;
  locale: Locale;
  navLinks: { href: string; label: string }[];
}) {
  const [open, setOpen] = useState(false);
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    document.body.style.overflow = "hidden";
    closeButtonRef.current?.focus();

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.body.style.overflow = "";
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open]);

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-label={content.nav.openMenu}
        className="rounded-md p-2 text-slate-600 hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 lg:hidden"
      >
        <Menu className="size-6" aria-hidden="true" />
      </button>

      {open && (
        <div className="fixed inset-0 z-[60] lg:hidden" role="dialog" aria-modal="true" aria-label={content.nav.primaryNav}>
          <div className="absolute inset-0 bg-slate-950/50" onClick={() => setOpen(false)} aria-hidden="true" />
          <div
            className="absolute inset-y-0 right-0 flex w-[88%] max-w-sm flex-col gap-6 overflow-y-auto bg-landing-canvas px-6 py-5 shadow-2xl"
            onClickCapture={(event) => {
              if ((event.target as HTMLElement).closest("a")) setOpen(false);
            }}
          >
            <div className="flex items-center justify-between">
              <LanguageSwitcher locale={locale} />
              <button
                ref={closeButtonRef}
                type="button"
                onClick={() => setOpen(false)}
                aria-label={content.nav.closeMenu}
                className="rounded-md p-2 text-slate-500 hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600"
              >
                <X className="size-5" aria-hidden="true" />
              </button>
            </div>

            <nav aria-label={content.nav.primaryNav} className="flex flex-col gap-1">
              {navLinks.map((link) => (
                <a
                  key={link.href}
                  href={link.href}
                  className="rounded-md px-2 py-3 text-base font-medium text-slate-800 hover:bg-slate-50"
                >
                  {link.label}
                </a>
              ))}
            </nav>

            <div className="mt-auto flex flex-col gap-3 border-t border-slate-100 pt-5">
              <Link href="/login" className={secondaryButton("md", "w-full")}>
                {content.nav.login}
              </Link>
              <a href={contact.whatsapp} target="_blank" rel="noopener noreferrer" className={primaryButton("md", "w-full")}>
                {content.nav.talkToUs}
              </a>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
