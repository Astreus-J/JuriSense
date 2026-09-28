import type { Metadata } from "next";

import { ComingSoon } from "@/components/shared/ComingSoon";
import { NAV_ITEMS } from "@/lib/navigation/modules";

export const metadata: Metadata = { title: "Evidence & Audit — JuriSense Gate" };

export default function EvidencePage() {
  const { icon, label, comingSoonDescription } = NAV_ITEMS.evidence;
  return <ComingSoon icon={icon} title={label} description={comingSoonDescription ?? ""} />;
}
