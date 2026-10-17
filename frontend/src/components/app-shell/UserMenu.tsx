"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Check, ChevronDown, LogOut, Monitor, Moon, Sun } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { cn } from "@/lib/cn";
import { useI18n } from "@/lib/i18n/client";
import type { MessageKey } from "@/lib/i18n/translate";
import type { Role } from "@/lib/auth/types";
import type { ThemePreference } from "@/lib/theme";
import { useDropdownMenu } from "./useDropdownMenu";
import { useThemePreference } from "./useThemePreference";

const THEME_OPTIONS: Array<{ value: ThemePreference; labelKey: MessageKey; icon: LucideIcon }> = [
  { value: "system", labelKey: "shell.themeSystem", icon: Monitor },
  { value: "light", labelKey: "shell.themeLight", icon: Sun },
  { value: "dark", labelKey: "shell.themeDark", icon: Moon },
];

interface UserMenuProps {
  fullName: string;
  email: string;
  role: Role;
}

export function UserMenu({ fullName, email, role }: UserMenuProps) {
  const router = useRouter();
  const { t } = useI18n();
  const { open, setOpen, containerRef, triggerRef, registerItem, handleItemKeyDown } =
    useDropdownMenu();
  const [signingOut, setSigningOut] = useState(false);
  const [theme, setTheme] = useThemePreference();

  async function handleSignOut() {
    setSigningOut(true);
    try {
      await fetch("/api/session/logout", { method: "POST" });
    } catch (error) {
      // #135: best-effort, same as the Route Handler's own "always clear the local
      // session no matter what" contract (`src/app/api/session/logout/route.ts`) -- a
      // network failure here must not surface as an unhandled promise rejection; the
      // user still gets signed out locally via the redirect below.
      console.error("Logout request failed", error);
    } finally {
      router.push("/login");
      router.refresh();
    }
  }

  return (
    <div ref={containerRef} className="relative">
      <button
        ref={triggerRef}
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
        className={cn(
          "flex items-center gap-2 rounded-md px-2 py-1 text-left text-sm",
          "hover:bg-surface-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring",
        )}
      >
        <span
          aria-hidden="true"
          className="flex size-7 shrink-0 items-center justify-center rounded-md bg-foreground text-xs font-semibold text-background"
        >
          {initials(fullName)}
        </span>
        <span className="hidden min-w-0 flex-col leading-tight sm:flex">
          <span className="truncate text-[14px] font-medium text-foreground">{fullName}</span>
          <span className="truncate text-xs text-foreground-muted">{t(`role.${role}`)}</span>
        </span>
        <span className="sr-only sm:hidden">{t("shell.accountMenu", { name: fullName })}</span>
        <ChevronDown className="size-3.5 shrink-0 text-foreground-muted" aria-hidden="true" />
      </button>

      {open && (
        <div
          role="menu"
          aria-label={t("shell.account")}
          className="absolute right-0 z-30 mt-1 w-60 rounded-md border border-border bg-surface-raised py-1 shadow-lg"
        >
          <div className="px-3 py-2" role="none">
            <p className="truncate text-sm font-medium text-foreground">{fullName}</p>
            <p className="truncate text-xs text-foreground-muted">{email}</p>
          </div>
          <div role="separator" className="my-1 border-t border-border" />
          <div role="group" aria-label={t("shell.theme")}>
            <p className="px-3 pb-1 pt-1.5 text-[12px] font-medium uppercase tracking-wider text-foreground-muted" aria-hidden="true">
              {t("shell.theme")}
            </p>
            {THEME_OPTIONS.map((option, index) => (
              <button
                key={option.value}
                ref={registerItem(index)}
                role="menuitemradio"
                aria-checked={theme === option.value}
                type="button"
                onKeyDown={handleItemKeyDown}
                onClick={() => setTheme(option.value)}
                className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-sm text-foreground hover:bg-surface-muted focus-visible:outline-none focus-visible:bg-surface-muted"
              >
                <option.icon className="size-4 shrink-0 text-foreground-muted" aria-hidden="true" />
                <span className="flex-1">{t(option.labelKey)}</span>
                {theme === option.value && (
                  <Check className="size-4 shrink-0 text-primary" aria-hidden="true" />
                )}
              </button>
            ))}
          </div>
          <div role="separator" className="my-1 border-t border-border" />
          <button
            ref={registerItem(THEME_OPTIONS.length)}
            role="menuitem"
            type="button"
            onKeyDown={handleItemKeyDown}
            onClick={handleSignOut}
            disabled={signingOut}
            className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-sm text-danger hover:bg-danger-surface focus-visible:outline-none focus-visible:bg-danger-surface disabled:opacity-60"
          >
            <LogOut className="size-4 shrink-0" aria-hidden="true" />
            {signingOut ? t("shell.signingOut") : t("shell.signOut")}
          </button>
        </div>
      )}
    </div>
  );
}

function initials(fullName: string): string {
  const parts = fullName.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
}
