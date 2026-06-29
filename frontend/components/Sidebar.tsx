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
    await createClient().auth.signOut();
    router.push("/login");
    router.refresh();
  };

  return (
    <>
      <button
        type="button"
        className="fixed top-4 left-4 z-50 flex h-9 w-9 items-center justify-center rounded-lg bg-zinc-800 text-zinc-300 md:hidden"
        onClick={() => setOpen(!open)}
        aria-label="Toggle navigation"
      >
        {open ? <X size={18} /> : <Menu size={18} />}
      </button>

      {open && (
        <div
          className="fixed inset-0 z-40 bg-black/60 md:hidden"
          onClick={() => setOpen(false)}
        />
      )}

      <aside
        className={[
          "fixed left-0 top-0 z-40 flex h-full w-60 flex-col border-r border-zinc-800 bg-zinc-900 transition-transform duration-200",
          open ? "translate-x-0" : "-translate-x-full",
          "md:translate-x-0",
        ].join(" ")}
      >
        <div className="flex h-14 items-center gap-2.5 border-b border-zinc-800 px-5">
          <BrainCircuit size={20} className="text-indigo-400" />
          <span className="text-sm font-semibold tracking-tight text-white">FinSight AI</span>
        </div>

        <nav className="flex flex-1 flex-col gap-0.5 overflow-y-auto p-3">
          {NAV.map(({ href, label, icon: Icon }) => {
            const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
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
              </Link>
            );
          })}
        </nav>

        <div className="border-t border-zinc-800 p-4">
          {userLabel && (
            <p className="mb-2 truncate text-xs font-medium text-zinc-300">{userLabel}</p>
          )}
          <div className="flex items-center justify-between gap-2">
            <div>
              <p className="text-[11px] text-zinc-600">Personal Finance Agent</p>
              <p className="text-[11px] text-zinc-700">Private · Local</p>
            </div>
            <div className="flex items-center gap-1">
              <ThemeToggle />
              {isSupabaseConfigured() && (
                <button
                  type="button"
                  onClick={() => void handleSignOut()}
                  className="flex h-8 w-8 items-center justify-center rounded-lg text-zinc-500 hover:bg-zinc-800 hover:text-zinc-200"
                  aria-label="Sign out"
                >
                  <LogOut size={14} />
                </button>
              )}
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}
