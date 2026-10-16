import { useCallback, useSyncExternalStore } from "react";

import { THEME_STORAGE_KEY, isThemePreference } from "@/lib/theme";
import type { ThemePreference } from "@/lib/theme";

const listeners = new Set<() => void>();

function subscribe(listener: () => void) {
  listeners.add(listener);
  window.addEventListener("storage", listener);
  return () => {
    listeners.delete(listener);
    window.removeEventListener("storage", listener);
  };
}

function readPreference(): ThemePreference {
  try {
    const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
    return isThemePreference(stored) ? stored : "system";
  } catch {
    return "system";
  }
}

/**
 * Reads/writes the persisted theme preference and mirrors it on <html data-theme>. "system"
 * removes the attribute so `prefers-color-scheme` applies (see globals.css). Storage access
 * is wrapped in try/catch: it throws in some privacy modes, and the toggle must still work
 * for the current page view in that case.
 */
export function useThemePreference(): [ThemePreference, (next: ThemePreference) => void] {
  const preference = useSyncExternalStore(subscribe, readPreference, () => "system" as const);

  const setPreference = useCallback((next: ThemePreference) => {
    const root = document.documentElement;
    if (next === "system") root.removeAttribute("data-theme");
    else root.setAttribute("data-theme", next);
    try {
      if (next === "system") window.localStorage.removeItem(THEME_STORAGE_KEY);
      else window.localStorage.setItem(THEME_STORAGE_KEY, next);
    } catch {
      // Not persisted; applies for this page view only.
    }
    listeners.forEach((listener) => listener());
  }, []);

  return [preference, setPreference];
}
