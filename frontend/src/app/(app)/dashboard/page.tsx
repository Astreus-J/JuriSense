import type { Metadata } from "next";

import { RoleDashboard } from "@/components/dashboard/RoleDashboard";
import { requireSession } from "@/lib/auth/session";

export const metadata: Metadata = {
  title: "Dashboard — JuriSense Gate",
};

export default async function DashboardPage() {
  // De-duped with the layout's own call via React's `cache()` — see
  // `src/lib/auth/session.ts`.
  const user = await requireSession();
  return <RoleDashboard fullName={user.fullName} role={user.role} />;
}
