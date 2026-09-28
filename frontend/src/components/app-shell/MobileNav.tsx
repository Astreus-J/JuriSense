"use client";

import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { Menu, X } from "lucide-react";

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
  const [open, setOpen] = useState(false);
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    document.body.style.overflow = "hidden";
    closeButtonRef.current?.focus();

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.body.style.overflow = "";
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open]);

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-label="Open navigation"
        className="rounded-md p-2 text-foreground-muted hover:bg-surface-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring md:hidden"
      >
        <Menu className="size-5" aria-hidden="true" />
      </button>

      {open && (
        <div className="fixed inset-0 z-40 md:hidden" role="dialog" aria-modal="true" aria-label="Navigation">
          <div
            className="absolute inset-0 bg-black/40"
            onClick={() => setOpen(false)}
            aria-hidden="true"
          />
          <div
            className="absolute inset-y-0 left-0 flex w-72 max-w-[80vw] flex-col bg-surface px-4 py-5 shadow-xl"
            // Closes the drawer whenever a nav link inside it is clicked,
            // without needing a callback prop passed across the Server/Client
            // boundary (`children` here is server-rendered `SidebarContent`).
            onClickCapture={(event) => {
              if ((event.target as HTMLElement).closest("a")) setOpen(false);
            }}
          >
            <div className="mb-6 flex items-center justify-between px-1">
              <Brand />
              <button
                ref={closeButtonRef}
                type="button"
                onClick={() => setOpen(false)}
                aria-label="Close navigation"
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
