"use client";

import { useSyncExternalStore } from "react";
import { Moon, Sun, Monitor } from "@phosphor-icons/react";

type Theme = "system" | "light" | "dark";
const themes: Theme[] = ["system", "light", "dark"];
const subscribe = (notify: () => void) => {
  window.addEventListener("geevi-theme", notify);
  window.addEventListener("storage", notify);
  return () => { window.removeEventListener("geevi-theme", notify); window.removeEventListener("storage", notify); };
};
function getTheme(): Theme {
  const value = document.documentElement.dataset.theme;
  return value === "light" || value === "dark" ? value : "system";
}
export function Appearance() {
  const theme = useSyncExternalStore(subscribe, getTheme, () => "system" as Theme);
  const next = themes[(themes.indexOf(theme) + 1) % themes.length];
  const Icon = theme === "dark" ? Moon : theme === "light" ? Sun : Monitor;
  return <button className="icon-button" type="button" title={`Theme: ${theme}. Switch to ${next}`} aria-label={`Theme: ${theme}. Switch to ${next}`} onClick={() => {
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem("geevi-theme", next); } catch { /* Theme still works when storage is unavailable. */ }
    window.dispatchEvent(new Event("geevi-theme"));
  }}><Icon aria-hidden="true" weight="regular" /></button>;
}
