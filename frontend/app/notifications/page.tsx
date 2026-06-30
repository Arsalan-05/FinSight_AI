"use client";

import { Bell, CheckCheck } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { PageHeader } from "@/components/ui/PageHeader";
import { useToast } from "@/contexts/ToastContext";
import { useAuthReady } from "@/hooks/useAuthReady";
import { api } from "@/lib/api";
import { chatUrl } from "@/lib/chat-url";
import type { AppNotification } from "@/lib/types";

export default function NotificationsPage() {
  const { toast } = useToast();
  const authReady = useAuthReady();
  const [items, setItems] = useState<AppNotification[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<"all" | "unread">("all");

  const load = useCallback(() => {
    return api
      .getNotifications()
      .then(setItems)
      .catch(() => setItems([]));
  }, []);

  useEffect(() => {
    if (!authReady) return;
    void load().finally(() => setLoading(false));
  }, [authReady, load]);

  const visible = items.filter((n) => filter === "all" || !n.read);
  const unread = items.filter((n) => !n.read).length;

  const markRead = async (id: string) => {
    await api.markNotificationRead(id);
    setItems((prev) => prev.map((n) => (n.id === id ? { ...n, read: true } : n)));
  };

  const markAll = async () => {
    await api.markAllNotificationsRead();
    await load();
    toast("All alerts marked read");
  };

  return (
    <div className="page-container max-w-3xl gap-6">
      <PageHeader
        eyebrow="Alerts"
        title="Notification"
        titleAccent="inbox"
        subtitle="Budget breaches, spend alerts, and advisor-triggered warnings."
        actions={
          unread > 0 ? (
            <button
              type="button"
              onClick={() => void markAll()}
              className="btn-ghost inline-flex items-center gap-2 text-sm"
            >
              <CheckCheck size={15} />
              Mark all read
            </button>
          ) : undefined
        }
      />

      <div className="flex gap-2">
        {(["all", "unread"] as const).map((key) => (
          <button
            key={key}
            type="button"
            onClick={() => setFilter(key)}
            className={[
              "rounded-lg px-3 py-1.5 text-xs font-medium capitalize",
              filter === key
                ? "bg-[var(--accent-soft)] text-[var(--accent)]"
                : "text-[var(--muted)] hover:bg-[var(--surface)]",
            ].join(" ")}
          >
            {key}
            {key === "unread" && unread > 0 ? ` (${unread})` : ""}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="space-y-2">
          <div className="h-16 shimmer rounded-xl" />
          <div className="h-16 shimmer rounded-xl" />
        </div>
      ) : visible.length === 0 ? (
        <div className="panel rounded-2xl p-8 text-center">
          <Bell size={28} className="mx-auto text-[var(--muted)]" />
          <p className="mt-3 text-sm text-[var(--muted)]">
            {filter === "unread" ? "No unread alerts." : "No alerts yet — set budgets to get spend warnings."}
          </p>
          <Link href="/" className="link-accent mt-3 inline-block text-xs">
            Back to overview
          </Link>
        </div>
      ) : (
        <ul className="flex flex-col gap-2">
          {visible.map((n) => (
            <li
              key={n.id}
              className={[
                "panel rounded-xl px-4 py-4",
                !n.read && "border-[var(--accent)]/30 bg-[var(--accent-soft)]/20",
                n.severity === "warning" && "border-amber-500/25",
              ]
                .filter(Boolean)
                .join(" ")}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-sm font-medium text-[var(--foreground)]">{n.title}</p>
                  <p className="mt-1 text-xs leading-relaxed text-[var(--muted)]">{n.body}</p>
                  <p className="mt-2 text-[10px] uppercase tracking-wider text-[var(--muted)]">
                    {n.kind.replace(/_/g, " ")}
                  </p>
                </div>
                <div className="flex shrink-0 flex-col items-end gap-2">
                  {!n.read && (
                    <button
                      type="button"
                      onClick={() => void markRead(n.id)}
                      className="btn-ghost px-2 py-1 text-xs"
                    >
                      Mark read
                    </button>
                  )}
                  <Link
                    href={chatUrl(`Help me with this alert: ${n.title}. ${n.body}`)}
                    className="link-accent text-xs"
                  >
                    Ask advisor
                  </Link>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
