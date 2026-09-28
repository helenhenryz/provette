/* The design tokens, read from the page so the 3D scene is coloured by the same values as
   everything else, in light and dark. Re-read when the theme changes. */

import { useEffect, useState } from "react";

export interface SceneTokens {
  bg: string;
  surface: string;
  surface2: string;
  border: string;
  text: string;
  muted: string;
  faint: string;
  link: string;
  error: string;
  warning: string;
  dark: boolean;
}

const FALLBACK: SceneTokens = {
  bg: "#ffffff",
  surface: "#f6f7f8",
  surface2: "#eceef1",
  border: "#dfe3e8",
  text: "#1a1d21",
  muted: "#5b6470",
  faint: "#737c88",
  link: "#1f5fbf",
  error: "#c7382f",
  warning: "#d97a13",
  dark: false,
};

export function readTokens(): SceneTokens {
  if (typeof window === "undefined" || typeof getComputedStyle !== "function")
    return FALLBACK;
  const style = getComputedStyle(document.documentElement);
  const read = (name: string, fallback: string) => {
    const v = style.getPropertyValue(name).trim();
    return /^#[0-9a-f]{6}$/i.test(v) ? v : fallback;
  };
  const bg = read("--bg", FALLBACK.bg);
  return {
    bg,
    surface: read("--surface", FALLBACK.surface),
    surface2: read("--surface-2", FALLBACK.surface2),
    border: read("--border", FALLBACK.border),
    text: read("--text", FALLBACK.text),
    muted: read("--muted", FALLBACK.muted),
    faint: read("--faint", FALLBACK.faint),
    link: read("--link", FALLBACK.link),
    error: read("--error", FALLBACK.error),
    warning: read("--warning", FALLBACK.warning),
    dark: parseInt(bg.slice(1, 3), 16) < 128,
  };
}

export function useTokens(): SceneTokens {
  const [tokens, setTokens] = useState<SceneTokens>(readTokens);
  useEffect(() => {
    const update = () => setTokens(readTokens());
    const observer =
      typeof MutationObserver === "function"
        ? new MutationObserver(update)
        : null;
    observer?.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["data-theme"],
    });
    const media =
      typeof window.matchMedia === "function"
        ? window.matchMedia("(prefers-color-scheme: dark)")
        : null;
    media?.addEventListener?.("change", update);
    update();
    return () => {
      observer?.disconnect();
      media?.removeEventListener?.("change", update);
    };
  }, []);
  return tokens;
}
