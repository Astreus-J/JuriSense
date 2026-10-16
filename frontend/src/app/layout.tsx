import type { Metadata } from "next";
import { Geist, Geist_Mono, Source_Serif_4 } from "next/font/google";
import "./globals.css";
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

export const metadata: Metadata = {
  title: "JuriSense Gate — Vendor & Contract Compliance, With Evidence",
  description:
    "JuriSense Gate turns contracts, supplier data, and your company's own policy into auditable, explainable compliance decisions — with AI, an executable policy engine, and blockchain-anchored evidence.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  // The root layout renders the single <html> for the whole app, including the English-only
  // authenticated app, so `lang` stays "en" here even on the translated marketing routes
  // (/pt, /es) -- `LandingPage.tsx` overrides it with a nested `lang` on its wrapping <div>,
  // which modern assistive tech honors for in-body content. Accepted tradeoff, not an
  // oversight: avoids wrapping the entire app (including /login, /(app)/*) in a locale
  // segment just for this.
  //
  // `suppressHydrationWarning` is scoped to <html> only: the inline script below sets
  // `data-theme` before first paint (no light/dark flash), which React would otherwise flag.
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${geistSans.variable} ${geistMono.variable} ${sourceSerif.variable} h-full antialiased`}
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
      </head>
      <body className="min-h-full flex flex-col bg-background text-foreground">{children}</body>
    </html>
  );
}
