import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
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
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
