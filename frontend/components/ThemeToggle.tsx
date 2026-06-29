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
      className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-[var(--border)] bg-[var(--surface)] text-[var(--muted)] transition-colors hover:border-[var(--border-strong)] hover:bg-[var(--surface-elevated)] hover:text-[var(--foreground)]"
    >
      {isDark ? <Sun size={14} /> : <Moon size={14} />}
    </button>
  );
}
