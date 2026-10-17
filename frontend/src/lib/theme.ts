/**
 * Theme preference: "system" (no `data-theme` attribute, follows `prefers-color-scheme`),
 * "light" or "dark". The choice is persisted in localStorage; the inline script below applies
 * it to <html> before first paint so there is no flash of the wrong theme.
 */
export const THEME_STORAGE_KEY = "jurisense-theme";

export const THEME_PREFERENCES = ["system", "light", "dark"] as const;
export type ThemePreference = (typeof THEME_PREFERENCES)[number];

export function isThemePreference(value: unknown): value is ThemePreference {
  return typeof value === "string" && (THEME_PREFERENCES as readonly string[]).includes(value);
}

/** Runs synchronously in <head>; localStorage can throw (privacy modes), hence the try/catch. */
export const THEME_INIT_SCRIPT = `(function(){try{var t=localStorage.getItem(${JSON.stringify(
  THEME_STORAGE_KEY,
)});if(t==="light"||t==="dark"){document.documentElement.setAttribute("data-theme",t);}}catch(e){}})();`;
