"use client";

import { Bell } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { useAuthReady } from "@/hooks/useAuthReady";
import { api } from "@/lib/api";
import { chatUrl } from "@/lib/chat-url";
import type { AppNotification } from "@/lib/types";

export function NotificationBell() {
  const authReady = useAuthReady();
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<AppNotification[]>([]);

  const load = useCallback(() => {
    return api.getNotifications().then(setItems).catch(() => setItems([]));
  }, []);

  useEffect(() => {
    if (!authReady) return;
    void load();
  }, [authReady, load]);

  const unread = items.filter((n) => !n.read).length;

  const markRead = async (id: string) => {
    await api.markNotificationRead(id);
    setItems((prev) => prev.map((n) => (n.id === id ? { ...n, read: true } : n)));
  };

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="icon-btn relative"
        aria-label="Notifications"
      >
        <Bell size={16} />
        {unread > 0 && (
          <span className="absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-rose-500 px-1 text-[10px] font-bold text-white">
            {unread > 9 ? "9+" : unread}
          </span>
        )}
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} aria-hidden />
          <div className="absolute right-0 z-50 mt-2 w-80 overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--surface-elevated)] shadow-xl">
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
              {items.length === 0 ? (
                <li className="px-4 py-8 text-center text-xs text-[var(--muted)]">No alerts yet</li>
              ) : (
                items.map((n) => (
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
                ))
              )}
            </ul>
            <div className="border-t border-[var(--border)] px-4 py-2">
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
