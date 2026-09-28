import type { Metadata } from "next";

import { ComingSoon } from "@/components/shared/ComingSoon";
import { NAV_ITEMS } from "@/lib/navigation/modules";

export const metadata: Metadata = { title: "Approvals — JuriSense Gate" };

export default function ApprovalsPage() {
  const { icon, label, comingSoonDescription } = NAV_ITEMS.approvals;
  return <ComingSoon icon={icon} title={label} description={comingSoonDescription ?? ""} />;
}
