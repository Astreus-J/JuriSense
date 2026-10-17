import type { Metadata } from "next";
import { Geist, Geist_Mono, Source_Serif_4 } from "next/font/google";
import "./globals.css";
import { I18nProvider } from "@/lib/i18n/client";
import { getMessages } from "@/lib/i18n/catalog";
import { HTML_LANG } from "@/lib/i18n/config";
import { getI18n } from "@/lib/i18n/server";
import { THEME_INIT_SCRIPT } from "@/lib/theme";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

// Page titles only (see PageHeader): a serif face gives the legal-tech product a document-like
// voice without any decoration. Loaded through next/font like Geist, so no new dependency.
const sourceSerif = Source_Serif_4({
  variable: "--font-source-serif",
  subsets: ["latin"],
  display: "swap",
});

// Default title/description for any route that doesn't set its own (the marketing landing page
// does, and overrides these).
export async function generateMetadata(): Promise<Metadata> {
  const { t } = await getI18n();
  return { title: t("meta.defaultTitle"), description: t("meta.defaultDescription") };
}

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  // `lang` follows the active app locale (`NEXT_LOCALE` cookie, see `src/lib/i18n`). Reading the
  // cookie makes every route dynamic, including the marketing landing page; the landing page
  // keeps its own `lang` on a wrapping <div> (`LandingPage.tsx`), so its in-body language is
  // still correct for assistive tech whatever the app locale cookie says.
  //
  // Only the ACTIVE locale's catalog is handed to the client provider, never every language.
  //
  // `suppressHydrationWarning` is scoped to <html> only: the inline script below sets
  // `data-theme` before first paint (no light/dark flash), which React would otherwise flag.
  const { locale } = await getI18n();

  return (
    <html
      lang={HTML_LANG[locale]}
      suppressHydrationWarning
      className={`${geistSans.variable} ${geistMono.variable} ${sourceSerif.variable} h-full antialiased`}
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
      </head>
      <body className="min-h-full flex flex-col bg-background text-foreground">
        <I18nProvider locale={locale} messages={getMessages(locale)}>
          {children}
        </I18nProvider>
      </body>
    </html>
  );
}
