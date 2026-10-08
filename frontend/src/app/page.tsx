import type { Metadata } from "next";
import LandingPage from "@/components/landing/LandingPage";
import { getLandingContent } from "@/lib/landing-content";

const content = getLandingContent("en");

export const metadata: Metadata = {
  title: content.meta.title,
  description: content.meta.description,
  alternates: {
    canonical: "/",
    languages: { en: "/", pt: "/pt", es: "/es" },
  },
  openGraph: {
    title: content.meta.title,
    description: content.meta.description,
    locale: "en_US",
    type: "website",
  },
};

export default function Home() {
  return <LandingPage locale="en" />;
}
