import type { Metadata } from "next";

import { ComingSoon } from "@/components/shared/ComingSoon";
import { NAV_ITEMS } from "@/lib/navigation/modules";

export const metadata: Metadata = { title: "Policies — JuriSense Gate" };

export default function PoliciesPage() {
  const { icon, label, comingSoonDescription } = NAV_ITEMS.policies;
  return <ComingSoon icon={icon} title={label} description={comingSoonDescription ?? ""} />;
}
