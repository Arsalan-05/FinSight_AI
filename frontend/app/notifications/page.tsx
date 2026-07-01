"use client";

import {
  Bell,
  CheckCheck,
  ChevronRight,
  Mail,
  Shield,
  Sparkles,
  TrendingUp,
} from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { BudgetsPanel } from "@/components/BudgetsPanel";
import { ToggleSwitch } from "@/components/ui/ToggleSwitch";
import { PageHeader } from "@/components/ui/PageHeader";
import { useToast } from "@/contexts/ToastContext";
import { useAuthReady } from "@/hooks/useAuthReady";
import { api } from "@/lib/api";
import { chatUrl } from "@/lib/chat-url";
import type { AlertPreferences, AppNotification, WeeklyBrief } from "@/lib/types";
import { formatDate } from "@/lib/utils";

const DEFAULT_ALERT_PREFS: AlertPreferences = {
  spend_alerts: true,
  email_digest: false,
};

export default function NotificationsPage() {
  const { toast } = useToast();
  const authReady = useAuthReady();
  const [items, setItems] = useState<AppNotification[]>([]);
  const [liveAlerts, setLiveAlerts] = useState<WeeklyBrief["alerts"]>([]);
  const [briefHeadline, setBriefHeadline] = useState<string | null>(null);
  const [alertPrefs, setAlertPrefs] = useState<AlertPreferences>(DEFAULT_ALERT_PREFS);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<"all" | "unread">("all");

  const load = useCallback(async () => {
    const [notifications, brief, prefs] = await Promise.all([
      api.getNotifications().catch(() => [] as AppNotification[]),
      api.getWeeklyBrief().catch(() => null),
      api.getAlertPreferences().catch(() => DEFAULT_ALERT_PREFS),
    ]);
    setItems(notifications);
    setLiveAlerts(brief?.alerts ?? []);
    setBriefHeadline(brief?.headline ?? null);
    setAlertPrefs(prefs);
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

  const togglePref = async (key: keyof AlertPreferences, value: boolean) => {
    const previous = alertPrefs;
    setAlertPrefs((prev) => ({ ...prev, [key]: value }));
    try {
      const updated = await api.updateAlertPreferences({ [key]: value });
      setAlertPrefs(updated);
      if (key === "spend_alerts" && value) {
        await load();
      }
    } catch {
      setAlertPrefs(previous);
      toast("Could not update alert preference", "error");
    }
  };

  if (!authReady || loading) {
    return (
      <div className="page-container max-w-3xl gap-6">
        <div className="h-24 shimmer rounded-2xl" />
        <div className="h-36 shimmer rounded-2xl" />
        <div className="h-48 shimmer rounded-2xl" />
      </div>
    );
  }

  return (
    <div className="page-container max-w-3xl gap-6">
      <PageHeader
        eyebrow="Alerts"
        title="Spending"
        titleAccent="alerts"
        subtitle="Live signals from your data, budget warnings, and saved notifications."
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

      <section className="panel rounded-2xl p-6">
        <div className="mb-4 flex items-start justify-between gap-3">
          <div className="flex gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[var(--accent-soft)]">
              <Sparkles size={18} className="text-[var(--accent)]" />
            </div>
            <div>
              <p className="eyebrow">Live signals</p>
              <h2 className="section-title mt-0.5">
                {briefHeadline ?? "This week at a glance"}
              </h2>
            </div>
          </div>
          <Link
            href={chatUrl("What should I focus on based on my recent alerts and spending?")}
            className="link-accent shrink-0 text-xs"
          >
            Ask Advisor →
          </Link>
        </div>

        {liveAlerts.length > 0 ? (
          <ul className="flex flex-col gap-2">
            {liveAlerts.map((a) => (
              <li
                key={a.id}
                className="flex items-start justify-between gap-3 rounded-xl border border-amber-500/25 bg-amber-500/5 px-4 py-3"
              >
                <div className="min-w-0">
                  <p className="text-sm font-medium text-[var(--foreground)]">{a.title}</p>
                  <p className="mt-0.5 text-xs leading-relaxed text-[var(--muted)]">{a.body}</p>
                </div>
                <Link
                  href={chatUrl(`Help me understand this spend alert: ${a.title}. ${a.body}`)}
                  className="shrink-0 text-[var(--muted)] hover:text-[var(--accent)]"
                  aria-label={`Ask about ${a.title}`}
                >
                  <ChevronRight size={16} />
                </Link>
              </li>
            ))}
          </ul>
        ) : (
          <div className="flex items-center gap-3 rounded-xl border border-emerald-500/20 bg-emerald-500/5 px-4 py-3">
            <TrendingUp size={18} className="shrink-0 text-emerald-500" />
            <p className="text-sm text-[var(--muted)]">
              No spending spikes, low runway warnings, or unusual charges detected this week.
            </p>
          </div>
        )}
      </section>

      <BudgetsPanel />

      <section className="flex flex-col gap-4">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Bell size={16} className="text-[var(--accent)]" />
            <h2 className="section-title">Saved alerts</h2>
          </div>
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
        </div>

        {visible.length === 0 ? (
          <div className="panel rounded-2xl p-8 text-center">
            <Bell size={28} className="mx-auto text-[var(--muted)]" />
            <p className="mt-3 text-sm text-[var(--muted)]">
              {filter === "unread"
                ? "No unread saved alerts."
                : "No saved alerts yet. Add monthly budgets above — you'll get warnings when you go over."}
            </p>
            {!alertPrefs.spend_alerts && (
              <p className="mt-2 text-xs text-amber-500">
                Spend alerts are turned off in preferences below.
              </p>
            )}
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
                      {n.created_at ? ` · ${formatDate(n.created_at)}` : ""}
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
      </section>

      <section className="panel rounded-2xl p-6">
        <div className="mb-4 flex items-center gap-2">
          <Shield size={16} className="text-[var(--accent)]" />
          <h2 className="section-title">Alert preferences</h2>
        </div>
        <div className="divide-y divide-[var(--border)]">
          <PrefToggle
            label="Spend alerts"
            desc="Notify when monthly spend exceeds a category budget"
            checked={alertPrefs.spend_alerts}
            onChange={(v) => void togglePref("spend_alerts", v)}
          />
          <PrefToggle
            label="Weekly email digest"
            desc="Monday summary of spending and alerts"
            checked={alertPrefs.email_digest}
            onChange={(v) => void togglePref("email_digest", v)}
          />
        </div>
        <Link href="/settings" className="link-accent mt-4 inline-flex items-center gap-1 text-xs">
          <Mail size={12} />
          More alert settings
        </Link>
      </section>
    </div>
  );
}

function PrefToggle({
  label,
  desc,
  checked,
  onChange,
}: {
  label: string;
  desc: string;
  checked: boolean;
  onChange: (value: boolean) => void;
}) {
  return (
    <label className="flex cursor-pointer items-center justify-between gap-4 py-3 first:pt-0 last:pb-0">
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-[var(--foreground)]">{label}</p>
        <p className="mt-0.5 text-xs text-[var(--muted)]">{desc}</p>
      </div>
      <ToggleSwitch checked={checked} onChange={onChange} label={label} />
    </label>
  );
}
