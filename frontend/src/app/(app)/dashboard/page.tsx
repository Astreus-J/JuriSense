import { RoleDashboard } from "@/components/dashboard/RoleDashboard";
import { requireSession } from "@/lib/auth/session";
import { pageTitle } from "@/lib/i18n/server";

export const generateMetadata = pageTitle("meta.dashboard");

export default async function DashboardPage() {
  // De-duped with the layout's own call via React's `cache()` — see
  // `src/lib/auth/session.ts`.
  const user = await requireSession();
  return <RoleDashboard fullName={user.fullName} role={user.role} />;
}
