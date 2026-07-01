"use client";

import { Bell } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { useAuthReady } from "@/hooks/useAuthReady";
import { api } from "@/lib/api";
import { chatUrl } from "@/lib/chat-url";
import type { AppNotification, WeeklyBrief } from "@/lib/types";

export function NotificationBell() {
  const authReady = useAuthReady();
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<AppNotification[]>([]);
  const [liveAlerts, setLiveAlerts] = useState<WeeklyBrief["alerts"]>([]);

  const load = useCallback(() => {
    return Promise.all([
      api.getNotifications().catch(() => [] as AppNotification[]),
      api.getWeeklyBrief().catch(() => null),
    ]).then(([notifications, brief]) => {
      setItems(notifications);
      setLiveAlerts(brief?.alerts ?? []);
    });
  }, []);

  useEffect(() => {
    if (!authReady) return;
    void load();
  }, [authReady, load]);

  const unread = items.filter((n) => !n.read).length;
  const badgeCount = unread + liveAlerts.length;

  const markRead = async (id: string) => {
    await api.markNotificationRead(id);
    setItems((prev) => prev.map((n) => (n.id === id ? { ...n, read: true } : n)));
  };

  const toggleOpen = () => {
    const next = !open;
    setOpen(next);
    if (next) void load();
  };

  return (
    <div className="relative">
      <button
        type="button"
        onClick={toggleOpen}
        className="icon-btn relative"
        aria-label="Notifications"
        aria-expanded={open}
      >
        <Bell size={16} />
        {badgeCount > 0 && (
          <span className="absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-rose-500 px-1 text-[10px] font-bold text-white">
            {badgeCount > 9 ? "9+" : badgeCount}
          </span>
        )}
      </button>

      {open && (
        <>
          <div
            className="fixed inset-0 z-[80]"
            onClick={() => setOpen(false)}
            aria-hidden
          />
          <div className="fixed right-4 top-[4.25rem] z-[90] w-[min(20rem,calc(100vw-2rem))] overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--surface-elevated)] shadow-xl md:top-5">
            <div className="flex items-center justify-between border-b border-[var(--border)] px-4 py-3">
              <p className="text-sm font-semibold text-[var(--foreground)]">Alerts</p>
              {unread > 0 && (
                <button
                  type="button"
                  onClick={() => void api.markAllNotificationsRead().then(load)}
                  className="text-xs text-[var(--accent)]"
                >
                  Mark all read
                </button>
              )}
            </div>
            <ul className="max-h-72 overflow-y-auto">
              {liveAlerts.length === 0 && items.length === 0 ? (
                <li className="px-4 py-8 text-center text-xs text-[var(--muted)]">
                  No alerts yet — set budgets on the Alerts page.
                </li>
              ) : (
                <>
                  {liveAlerts.map((a) => (
                    <li key={a.id}>
                      <Link
                        href={chatUrl(`Help me understand this spend alert: ${a.title}. ${a.body}`)}
                        onClick={() => setOpen(false)}
                        className="block w-full border-l-2 border-amber-500/50 bg-amber-500/5 px-4 py-3 text-left transition-colors hover:bg-[var(--surface)]"
                      >
                        <p className="text-[10px] font-medium uppercase tracking-wider text-amber-500">
                          Live signal
                        </p>
                        <p className="text-sm font-medium text-[var(--foreground)]">{a.title}</p>
                        <p className="mt-0.5 text-xs text-[var(--muted)]">{a.body}</p>
                      </Link>
                    </li>
                  ))}
                  {items.map((n) => (
                    <li key={n.id}>
                      <button
                        type="button"
                        onClick={() => void markRead(n.id)}
                        className={[
                          "w-full px-4 py-3 text-left transition-colors hover:bg-[var(--surface)]",
                          !n.read && "bg-[var(--accent-soft)]/30",
                        ].join(" ")}
                      >
                        <p className="text-sm font-medium text-[var(--foreground)]">{n.title}</p>
                        <p className="mt-0.5 text-xs text-[var(--muted)]">{n.body}</p>
                      </button>
                    </li>
                  ))}
                </>
              )}
            </ul>
            <div className="flex items-center justify-between border-t border-[var(--border)] px-4 py-2">
              <Link
                href="/notifications"
                className="link-accent text-xs"
                onClick={() => setOpen(false)}
              >
                View all alerts
              </Link>
              <Link
                href={chatUrl("What should I focus on based on my recent alerts and spending?")}
                className="link-accent text-xs"
                onClick={() => setOpen(false)}
              >
                Ask Advisor →
              </Link>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
