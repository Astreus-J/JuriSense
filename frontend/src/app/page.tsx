import type { Metadata } from "next";
import LandingPage from "@/components/landing/LandingPage";
import { getLandingContent } from "@/lib/landing-content";

const content = getLandingContent("en");

export const metadata: Metadata = {
  title: content.meta.title,
  description: content.meta.description,
};

export default function Home() {
  return <LandingPage locale="en" />;
}
