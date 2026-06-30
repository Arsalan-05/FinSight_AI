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
      className="icon-btn"
    >
      {isDark ? <Sun size={14} /> : <Moon size={14} />}
    </button>
  );
}
