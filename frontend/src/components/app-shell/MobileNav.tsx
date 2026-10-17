"use client";

import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { Menu, X } from "lucide-react";

import { useI18n } from "@/lib/i18n/client";
import { Brand } from "./Brand";

interface MobileNavProps {
  children: ReactNode;
}

/**
 * The mobile equivalent of `DesktopSidebar`: a hamburger trigger (visible
 * only below the `md` breakpoint) that opens a full-height drawer with the
 * same nav content. `children` is the server-rendered `SidebarContent` —
 * see the "Interleaving Server and Client Components" pattern in
 * `node_modules/next/dist/docs/01-app/01-getting-started/05-server-and-
 * client-components.md`.
 */
export function MobileNav({ children }: MobileNavProps) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const trigger = triggerRef.current;
    document.body.style.overflow = "hidden";
    closeButtonRef.current?.focus();

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false);
        return;
      }
      if (event.key !== "Tab" || !panelRef.current) return;
      // Focus trap: keep Tab / Shift+Tab inside the drawer while it is open.
      const focusable = panelRef.current.querySelectorAll<HTMLElement>(
        'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])',
      );
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      const active = document.activeElement;
      if (event.shiftKey && (active === first || !panelRef.current.contains(active))) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && (active === last || !panelRef.current.contains(active))) {
        event.preventDefault();
        first.focus();
      }
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.body.style.overflow = "";
      document.removeEventListener("keydown", handleKeyDown);
      // Restore focus to the control that opened the drawer.
      trigger?.focus();
    };
  }, [open]);

  return (
    <>
      <button
        ref={triggerRef}
        type="button"
        onClick={() => setOpen(true)}
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-label={t("shell.openNavigation")}
        className="rounded-md p-2 text-foreground-muted hover:bg-surface-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring md:hidden"
      >
        <Menu className="size-5" aria-hidden="true" />
      </button>

      {open && (
        <div className="fixed inset-0 z-40 md:hidden" role="dialog" aria-modal="true" aria-label={t("shell.navigation")}>
          <div
            className="absolute inset-0 bg-black/40"
            onClick={() => setOpen(false)}
            aria-hidden="true"
          />
          <div
            ref={panelRef}
            className="absolute inset-y-0 left-0 flex w-72 max-w-[85vw] flex-col overflow-y-auto sidebar-surface px-3 py-4 shadow-xl"
            // Closes the drawer whenever a nav link inside it is clicked,
            // without needing a callback prop passed across the Server/Client
            // boundary (`children` here is server-rendered `SidebarContent`).
            onClickCapture={(event) => {
              if ((event.target as HTMLElement).closest("a")) setOpen(false);
            }}
          >
            <div className="mb-5 flex items-center justify-between px-1">
              <Brand onDark />
              <button
                ref={closeButtonRef}
                type="button"
                onClick={() => setOpen(false)}
                aria-label={t("shell.closeNavigation")}
                className="rounded-md p-1.5 text-foreground-muted hover:bg-surface-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring"
              >
                <X className="size-5" aria-hidden="true" />
              </button>
            </div>
            {children}
          </div>
        </div>
      )}
    </>
  );
}
