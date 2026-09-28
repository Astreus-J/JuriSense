import type { Metadata } from "next";

import { ComingSoon } from "@/components/shared/ComingSoon";
import { NAV_ITEMS } from "@/lib/navigation/modules";

export const metadata: Metadata = { title: "Contracts — JuriSense Gate" };

export default function ContractsPage() {
  const { icon, label, comingSoonDescription } = NAV_ITEMS.contracts;
  return <ComingSoon icon={icon} title={label} description={comingSoonDescription ?? ""} />;
}
