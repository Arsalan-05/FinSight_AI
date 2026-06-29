"use client";

import { Moon, Sun } from "lucide-react";

import { setTheme, useThemeState } from "@/lib/theme";

export default function ThemeToggle() {
  const theme = useThemeState();
  const isDark = theme === "dark";

  return (
    <button
      type="button"
      onClick={() => setTheme(isDark ? "light" : "dark")}
      aria-label="Toggle theme"
      className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-zinc-800 bg-zinc-900 text-zinc-500 transition-colors hover:border-zinc-600 hover:bg-zinc-800 hover:text-zinc-200"
    >
      {isDark ? <Sun size={14} /> : <Moon size={14} />}
    </button>
  );
}
