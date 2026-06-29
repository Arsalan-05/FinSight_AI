"use client";

import { useSyncExternalStore } from "react";

const STORAGE_KEY = "finsight-theme";

export type Theme = "light" | "dark";

const listeners = new Set<() => void>();

function emitChange() {
  listeners.forEach((listener) => listener());
}

function subscribe(onChange: () => void) {
  listeners.add(onChange);
  return () => listeners.delete(onChange);
}

export function getStoredTheme(): Theme {
  if (typeof window === "undefined") return "dark";
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored === "light" ? "light" : "dark";
  } catch {
    return "dark";
  }
}

export function applyTheme(theme: Theme) {
  document.documentElement.setAttribute("data-theme", theme);
}

export function setTheme(theme: Theme) {
  try {
    localStorage.setItem(STORAGE_KEY, theme);
  } catch {
    // ignore quota / private mode
  }
  applyTheme(theme);
  emitChange();
}

export function useThemeState(): Theme {
  return useSyncExternalStore(subscribe, getStoredTheme, () => "dark");
}
