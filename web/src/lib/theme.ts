/* Light, dark or the system's choice, remembered per browser; dark until the reader picks. A
   choice of "System" is remembered too, so it is not taken back to dark. `?theme=light` on any
   URL sets it, which is handy for a screenshot. The tokens (src/tokens.css) do the rest, and
   index.html sets the same default before the page draws, so it never flashes light. */

export type Theme = "auto" | "light" | "dark";
const KEY = "provette.theme";
export const DEFAULT_THEME: Theme = "dark";

export function readTheme(): Theme {
  try {
    const fromUrl = new URLSearchParams(window.location.search).get("theme");
    if (fromUrl === "light" || fromUrl === "dark" || fromUrl === "auto") {
      localStorage.setItem(KEY, fromUrl);
      return fromUrl;
    }
    const stored = localStorage.getItem(KEY);
    if (stored === "light" || stored === "dark" || stored === "auto")
      return stored;
  } catch {
    /* no storage */
  }
  return DEFAULT_THEME;
}

export function applyTheme(theme: Theme): void {
  const root = document.documentElement;
  if (theme === "auto") delete root.dataset.theme;
  else root.dataset.theme = theme;
  try {
    localStorage.setItem(KEY, theme);
  } catch {
    /* no storage */
  }
}
