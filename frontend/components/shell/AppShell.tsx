"use client";

import {
  Bell,
  CreditCard,
  LayoutDashboard,
  LineChart,
  LogOut,
  Menu,
  MessageSquare,
  Search,
  Settings,
  Receipt,
  Users,
  X,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState, type CSSProperties } from "react";

import { BetaBanner } from "@/components/BetaBanner";
import { LogoMark, LogoWordmark } from "@/components/brand/Logo";
import { InstallPrompt } from "@/components/InstallPrompt";
import { NotificationBell } from "@/components/NotificationBell";
import ThemeToggle from "@/components/ThemeToggle";
import { createClient, isSupabaseConfigured } from "@/lib/supabase/client";

const NAV = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/analytics", label: "Analytics", icon: LineChart },
  { href: "/transactions", label: "Transactions", icon: CreditCard },
  { href: "/accounts", label: "Accounts", icon: Users },
  { href: "/subscriptions", label: "Subscriptions", icon: Receipt },
  { href: "/notifications", label: "Alerts", icon: Bell },
  { href: "/search", label: "Search", icon: Search },
  { href: "/chat", label: "Advisor", icon: MessageSquare },
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
    await createClient().auth.signOut();
    router.push("/login");
    router.refresh();
  };

  return (
    <>
      <div className="mesh-bg" aria-hidden>
        <div className="mesh-orb mesh-orb--cyan" />
      </div>
      <div className="grain" aria-hidden />

      <button
        type="button"
        className="fixed top-5 left-5 z-50 flex h-10 w-10 items-center justify-center rounded-xl glass panel-interactive md:hidden"
        onClick={() => setOpen(!open)}
        aria-label="Toggle navigation"
      >
        {open ? <X size={18} /> : <Menu size={18} />}
      </button>

      {open && (
        <div
          className="fixed inset-0 z-40 bg-black/55 backdrop-blur-md md:hidden"
          onClick={() => setOpen(false)}
        />
      )}

      <aside
        className={[
          "fixed left-0 top-0 z-40 flex h-full w-64 flex-col border-r border-[var(--border)] glass",
          "transition-transform duration-300 ease-[cubic-bezier(0.22,1,0.36,1)]",
          open ? "translate-x-0" : "-translate-x-full",
          "md:translate-x-0",
        ].join(" ")}
      >
        <div className="flex h-16 shrink-0 items-center gap-3 border-b border-[var(--border)] px-5">
          <Link href="/" className="flex min-w-0 items-center gap-3">
            <span className="shrink-0 overflow-hidden rounded-xl">
              <LogoMark size={36} />
            </span>
            <LogoWordmark />
          </Link>
        </div>

        <nav className="flex flex-1 flex-col gap-0.5 overflow-y-auto p-3">
          {NAV.map(({ href, label, icon: Icon }, i) => {
            const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                onClick={() => setOpen(false)}
                className={[
                  "nav-item stagger-item",
                  active ? "nav-item--active" : "nav-item--idle",
                ].join(" ")}
                style={{ "--stagger": i + 1 } as CSSProperties}
              >
                <Icon
                  size={16}
                  className={active ? "text-[var(--accent)]" : "opacity-75 group-hover:opacity-100"}
                />
                <span className="truncate">{label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="shrink-0 border-t border-[var(--border)] p-4">
          <div className="panel rounded-xl px-3 py-3">
            <div className="mb-2.5 min-w-0">
              <p className="truncate text-xs font-semibold text-[var(--foreground)]">
                {userLabel || "Your account"}
              </p>
              <p className="mt-1 truncate text-[10px] text-[var(--muted)]">
                Secured sign-in
              </p>
            </div>
            <div className="flex items-center gap-2">
              <NotificationBell />
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

      <div className={`min-h-screen md:pl-64 ${pathname.startsWith("/chat") ? "md:px-4" : ""}`}>
        <BetaBanner />
        <main
          className={[
            "min-h-screen pb-10 pt-[4.5rem] md:pt-8",
            pathname.startsWith("/chat") ? "px-4 md:px-6" : "px-4 md:px-8",
          ].join(" ")}
        >
          {children}
        </main>
      </div>
      <InstallPrompt />
    </>
  );
}
