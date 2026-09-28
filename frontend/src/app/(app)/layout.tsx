import type { Metadata } from "next";
import type { ReactNode } from "react";

import { AppShell } from "@/components/app-shell/AppShell";
import { requireSession } from "@/lib/auth/session";

export const metadata: Metadata = {
  description: "JuriSense Gate — vendor, contract, and compliance decisions, backed by evidence.",
};

/**
 * Root layout for every authenticated route (STORY-1.2.1). `requireSession()`
 * redirects to `/login` when there is no valid session — see
 * `src/lib/auth/session.ts` and `src/proxy.ts` for the full auth-guard
 * picture (proxy does the optimistic, pre-render check + silent refresh;
 * this is the authoritative check backed by an actual `/auth/me` call).
 */
export default async function AuthenticatedLayout({ children }: { children: ReactNode }) {
  const user = await requireSession();
  return <AppShell user={user}>{children}</AppShell>;
}
