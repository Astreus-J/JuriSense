import type { Metadata } from "next";

import { ComingSoon } from "@/components/shared/ComingSoon";
import { NAV_ITEMS } from "@/lib/navigation/modules";

export const metadata: Metadata = { title: "Suppliers — JuriSense Gate" };

export default function SuppliersPage() {
  const { icon, label, comingSoonDescription } = NAV_ITEMS.suppliers;
  return <ComingSoon icon={icon} title={label} description={comingSoonDescription ?? ""} />;
}
