"use client";

import type { ReactNode } from "react";
import Image from "next/image";

import { Brand } from "@/components/app-shell/Brand";
import { LocaleSwitcher } from "@/components/i18n/LocaleSwitcher";
import { useI18n } from "@/lib/i18n/client";

interface AuthShellProps {
  heading: string;
  subtext?: string;
  children: ReactNode;
  footer?: ReactNode;
  /** Show the language picker above the card. Default true; /login opts out. */
  showLocaleSwitcher?: boolean;
}

/**
 * Shared layout for the unauthenticated auth screens (login, invite acceptance, their error
 * boundaries): ONE bordered container split into a visual panel (`image.jpg`, roughly
 * 5/12) and the form panel (7/12) with a narrow centered column. Below `lg` the visual panel is
 * hidden and the form panel stands alone, with the brand shown above the heading instead.
 *
 * The image is purely decorative (`alt=""`): the tagline over it carries the meaning. The brand lives in the form panel at every width.
 * The picture (`image.jpg`, portrait 1088x1456, close to the panel's own proportions) is absolutely
 * positioned over the panel (the card's stretched grid cell) with `size-full object-cover`: it
 * spans the panel edge to edge at any card height, crops only a sliver, and the card's
 * `overflow-hidden` + radius clip it. It goes through Next's optimizer (resized per `sizes`, so the
 * panel does not ship the full original). Do NOT switch it to next/image `fill` or an inline `style`:
 * the CSP blocks inline style attributes. The page itself is kept compact
 * (`min-h-dvh`, small vertical padding) so the login does not need to scroll.
 */
export function AuthShell({ heading, subtext, children, footer, showLocaleSwitcher = true }: AuthShellProps) {
  const { t } = useI18n();

  return (
    <div className="flex min-h-dvh items-center justify-center bg-canvas px-4 py-4">
      <div className="w-full max-w-4xl space-y-3">
        {showLocaleSwitcher && (
          <div className="flex justify-end">
            <LocaleSwitcher />
          </div>
        )}

        <div className="grid overflow-hidden rounded-3xl border border-border bg-surface shadow-sm lg:min-h-[30rem] lg:grid-cols-12">
          <div className="sidebar-surface relative hidden overflow-hidden bg-transparent! lg:col-span-5 lg:block">
            {/* Sized with classes only: the CSP (`style-src 'self'`, next.config.ts) blocks inline
                style attributes, which silently broke next/image's `fill` mode (its sizing is an
                inline style), leaving the picture at its intrinsic height. */}
            <Image
              src="/img/image.jpg"
              alt=""
              width={1088}
              height={1456}
              priority
              sizes="(min-width: 1024px) 400px, 0px"
              className="absolute inset-0 size-full object-cover object-center"
            />
            <div className="relative flex h-full flex-col justify-between">
              <div />
              <p className="bg-[#0f172b]/85 px-6 py-5 text-sm leading-relaxed text-foreground">{t("auth.tagline")}</p>
            </div>
          </div>

          <div className="flex flex-col justify-center px-6 py-8 sm:px-12 lg:col-span-7 lg:px-14">
            <div className="mx-auto w-full max-w-sm space-y-6">
              <div className="space-y-5">
                <Brand />
                <div className="space-y-1.5">
                  <h1 className="font-serif text-2xl font-semibold tracking-tight text-foreground">{heading}</h1>
                  {subtext && <p className="text-sm text-foreground-muted">{subtext}</p>}
                </div>
              </div>
              {children}
              {footer && <div className="text-sm text-foreground-muted">{footer}</div>}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
