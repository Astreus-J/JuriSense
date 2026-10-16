import type { ReactNode } from "react";

import { Brand } from "@/components/app-shell/Brand";

interface AuthShellProps {
  heading: string;
  subtext?: string;
  children: ReactNode;
  footer?: ReactNode;
}

/**
 * Shared centered layout for the two unauthenticated auth screens
 * (login, invite acceptance). Deliberately plain: no marketing copy,
 * no imagery — this is a utility screen, not a landing page (the
 * "calm, precise" visual direction from the frontend-engineer persona /
 * `docs/00-project/principles.md`, and distinct on purpose from
 * `frontend/src/components/landing/*`, which is the pre-pivot product and
 * out of scope for this story).
 */
export function AuthShell({ heading, subtext, children, footer }: AuthShellProps) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-surface-muted px-4 py-12">
      <div className="w-full max-w-sm space-y-6">
        <Brand className="justify-center" />

        <div className="rounded-lg border border-border bg-surface p-6">
          <div className="mb-6 space-y-1 text-center">
            <h1 className="font-serif text-2xl font-semibold tracking-tight text-foreground">{heading}</h1>
            {subtext && <p className="text-sm text-foreground-muted">{subtext}</p>}
          </div>
          {children}
        </div>

        {footer && <div className="text-center text-sm text-foreground-muted">{footer}</div>}
      </div>
    </div>
  );
}
