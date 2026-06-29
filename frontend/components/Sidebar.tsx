"use client";

import {
  BrainCircuit,
  CreditCard,
  LayoutDashboard,
  LineChart,
  Menu,
  MessageSquare,
  Moon,
  Search,
  Settings,
  Sun,
  Users,
  X,
} from "lucide-react";
import Link from "next/link";
import { useTheme } from "next-themes";
import { usePathname } from "next/navigation";
import { useState } from "react";

const NAV: {
  href: string;
  label: string;
  icon: typeof LayoutDashboard;
  badge?: string;
}[] = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/analytics", label: "Analytics", icon: LineChart },
  { href: "/transactions", label: "Transactions", icon: CreditCard },
  { href: "/accounts", label: "Accounts", icon: Users },
  { href: "/search", label: "AI Search", icon: Search },
  { href: "/chat", label: "Chat Agent", icon: MessageSquare },
  { href: "/settings", label: "Settings", icon: Settings },
];

export default function Sidebar() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const { setTheme, resolvedTheme } = useTheme();
  const isDark = resolvedTheme !== "light";

  return (
    <>
      {/* Mobile toggle */}
      <button
        className="fixed top-4 left-4 z-50 flex h-9 w-9 items-center justify-center rounded-lg bg-zinc-800 text-zinc-300 md:hidden"
        onClick={() => setOpen(!open)}
        aria-label="Toggle navigation"
      >
        {open ? <X size={18} /> : <Menu size={18} />}
      </button>

      {/* Overlay */}
      {open && (
        <div
          className="fixed inset-0 z-40 bg-black/60 md:hidden"
          onClick={() => setOpen(false)}
        />
      )}

      {/* Sidebar panel */}
      <aside
        className={[
          "fixed left-0 top-0 z-40 flex h-full w-60 flex-col border-r border-zinc-800 bg-zinc-900 transition-transform duration-200",
          open ? "translate-x-0" : "-translate-x-full",
          "md:translate-x-0",
        ].join(" ")}
      >
        {/* Logo */}
        <div className="flex h-14 items-center gap-2.5 border-b border-zinc-800 px-5">
          <BrainCircuit size={20} className="text-indigo-400" />
          <span className="text-sm font-semibold tracking-tight text-white">
            FinSight AI
          </span>
        </div>

        {/* Nav links */}
        <nav className="flex flex-1 flex-col gap-0.5 p-3">
          {NAV.map(({ href, label, icon: Icon, badge }) => {
            const active =
              href === "/" ? pathname === "/" : pathname.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                onClick={() => setOpen(false)}
                className={[
                  "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                  active
                    ? "bg-indigo-600/20 text-indigo-300"
                    : "text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100",
                ].join(" ")}
              >
                <Icon size={16} />
                <span className="flex-1">{label}</span>
                {badge && (
                  <span className="rounded-full bg-zinc-800 px-2 py-0.5 text-[10px] text-zinc-500">
                    {badge}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="border-t border-zinc-800 p-4 flex items-center justify-between gap-2">
          <div>
            <p className="text-[11px] text-zinc-600">Personal Finance Agent</p>
            <p className="text-[11px] text-zinc-700">Claude + Voyage AI</p>
          </div>
          {/* Theme toggle — hidden until hydration (resolvedTheme is undefined on server) */}
          {resolvedTheme && (
            <button
              onClick={() => setTheme(isDark ? "light" : "dark")}
              aria-label="Toggle theme"
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-zinc-800 bg-zinc-900 text-zinc-500 transition-colors hover:border-zinc-600 hover:bg-zinc-800 hover:text-zinc-200"
            >
              {isDark ? <Sun size={14} /> : <Moon size={14} />}
            </button>
          )}
        </div>
      </aside>
    </>
  );
}
