"use client";

import {
  BrainCircuit,
  CreditCard,
  LayoutDashboard,
  LineChart,
  LogOut,
  Menu,
  MessageSquare,
  Search,
  Settings,
  Users,
  X,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import ThemeToggle from "@/components/ThemeToggle";
import { createClient, isSupabaseConfigured } from "@/lib/supabase/client";

const NAV = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/analytics", label: "Analytics", icon: LineChart },
  { href: "/transactions", label: "Transactions", icon: CreditCard },
  { href: "/accounts", label: "Accounts", icon: Users },
  { href: "/search", label: "AI Search", icon: Search },
  { href: "/chat", label: "AI Agent", icon: MessageSquare },
  { href: "/settings", label: "Settings", icon: Settings },
];

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [userLabel, setUserLabel] = useState("");

  useEffect(() => {
    if (!isSupabaseConfigured()) return;
    const supabase = createClient();
    void supabase.auth.getUser().then(({ data }) => {
      const u = data.user;
      if (!u) return;
      setUserLabel(
        u.user_metadata?.full_name ?? u.user_metadata?.name ?? u.email?.split("@")[0] ?? "User",
      );
    });
  }, []);

  const handleSignOut = async () => {
    if (!isSupabaseConfigured()) return;
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push("/login");
    router.refresh();
  };

  return (
    <>
      <div className="mesh-bg" aria-hidden />

      <button
        type="button"
        className="fixed top-5 left-5 z-50 flex h-10 w-10 items-center justify-center rounded-xl glass md:hidden"
        onClick={() => setOpen(!open)}
        aria-label="Toggle navigation"
      >
        {open ? <X size={18} /> : <Menu size={18} />}
      </button>

      {open && (
        <div
          className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm md:hidden"
          onClick={() => setOpen(false)}
        />
      )}

      <aside
        className={[
          "fixed left-0 top-0 z-40 flex h-full w-64 flex-col border-r border-[var(--border)] glass transition-transform duration-300",
          open ? "translate-x-0" : "-translate-x-full",
          "md:translate-x-0",
        ].join(" ")}
      >
        <div className="flex h-16 shrink-0 items-center gap-3 border-b border-[var(--border)] px-5">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 shadow-lg shadow-indigo-500/25">
            <BrainCircuit size={18} className="text-white" />
          </div>
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold tracking-tight">FinSight</p>
            <p className="text-[10px] uppercase tracking-[0.2em] text-[var(--muted)]">Private</p>
          </div>
        </div>

        <nav className="flex flex-1 flex-col gap-1 overflow-y-auto p-3">
          {NAV.map(({ href, label, icon: Icon }) => {
            const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                onClick={() => setOpen(false)}
                className={[
                  "group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all",
                  active ? "nav-link-active" : "nav-link-idle",
                ].join(" ")}
              >
                <Icon size={16} className={active ? "text-indigo-500" : "opacity-70 group-hover:opacity-100"} />
                <span className="truncate">{label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="shrink-0 border-t border-[var(--border)] p-4">
          <div className="card space-y-3 p-3">
            <div className="min-w-0">
              <p className="truncate text-xs font-medium text-[var(--foreground)]">
                {userLabel || "FinSight User"}
              </p>
              <p className="truncate text-[10px] text-[var(--muted)]">Personal workspace</p>
            </div>
            <div className="flex items-center gap-2">
              <ThemeToggle />
              {isSupabaseConfigured() && (
                <button
                  type="button"
                  onClick={() => void handleSignOut()}
                  className="btn-ghost flex flex-1 items-center justify-center gap-1.5 rounded-lg px-2 py-1.5 text-xs text-[var(--muted)]"
                  aria-label="Sign out"
                >
                  <LogOut size={13} />
                  Sign out
                </button>
              )}
            </div>
          </div>
        </div>
      </aside>

      <div className="min-h-screen md:pl-64">
        <main className="min-h-screen px-4 pb-10 pt-[4.5rem] md:px-8 md:pt-8">{children}</main>
      </div>
    </>
  );
}
