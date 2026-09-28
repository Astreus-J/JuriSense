import type { Metadata } from "next";

import { ComingSoon } from "@/components/shared/ComingSoon";
import { NAV_ITEMS } from "@/lib/navigation/modules";

export const metadata: Metadata = { title: "Integrations — JuriSense Gate" };

export default function IntegrationsPage() {
  const { icon, label, comingSoonDescription } = NAV_ITEMS.integrations;
  return <ComingSoon icon={icon} title={label} description={comingSoonDescription ?? ""} />;
}
