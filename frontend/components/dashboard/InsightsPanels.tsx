"use client";

import { Bell, ChevronRight, Newspaper } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import type { WeeklyBrief } from "@/lib/types";

export function WeeklyBriefPanel({ stagger = 1 }: { stagger?: number }) {
  const [brief, setBrief] = useState<WeeklyBrief | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    api
      .getWeeklyBrief()
      .then((data) => {
        if (active) setBrief(data);
      })
      .catch(() => {
        if (active) setBrief(null);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  if (loading) {
    return <div className="panel h-40 shimmer rounded-2xl" />;
  }
  if (!brief || brief.sections.length === 0) return null;

  return (
    <section
      className="panel panel-glow stagger-item rounded-2xl p-6"
      style={{ "--stagger": stagger } as React.CSSProperties}
    >
      <div className="mb-4 flex items-start justify-between gap-4">
        <div className="flex gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[var(--accent-soft)]">
            <Newspaper size={18} className="text-[var(--accent)]" />
          </div>
          <div>
            <p className="eyebrow">Weekly brief</p>
            <h2 className="section-title mt-0.5">{brief.headline}</h2>
          </div>
        </div>
        <Link href="/chat" className="link-accent shrink-0 text-xs">
          Ask Advisor →
        </Link>
      </div>
      <ul className="grid gap-2 sm:grid-cols-2">
        {brief.sections.map((s) => (
          <li
            key={s.id}
            className="rounded-xl border border-[var(--border)] bg-[var(--surface)] px-4 py-3"
          >
            <p className="text-[10px] font-medium uppercase tracking-wider text-[var(--muted)]">
              {s.label}
            </p>
            <p className="mt-1 text-sm text-[var(--foreground)]">{s.value}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}

export function SpendAlertsPanel({ stagger = 2 }: { stagger?: number }) {
  const [alerts, setAlerts] = useState<WeeklyBrief["alerts"]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    api
      .getWeeklyBrief()
      .then((data) => {
        if (active) setAlerts(data.alerts);
      })
      .catch(() => {
        if (active) setAlerts([]);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  if (loading || alerts.length === 0) return null;

  return (
    <section
      className="stagger-item rounded-2xl border border-amber-500/25 bg-amber-500/5 p-5"
      style={{ "--stagger": stagger } as React.CSSProperties}
    >
      <div className="mb-3 flex items-center gap-2">
        <Bell size={16} className="text-amber-400" />
        <h2 className="text-sm font-semibold text-[var(--foreground)]">Spend alerts</h2>
      </div>
      <ul className="flex flex-col gap-2">
        {alerts.map((a) => (
          <li key={a.id} className="flex items-start justify-between gap-3 rounded-xl bg-[var(--surface)]/60 px-4 py-3">
            <div>
              <p className="text-sm font-medium text-[var(--foreground)]">{a.title}</p>
              <p className="mt-0.5 text-xs text-[var(--muted)]">{a.body}</p>
            </div>
            <Link href="/chat" className="shrink-0 text-[var(--muted)] hover:text-[var(--accent)]">
              <ChevronRight size={16} />
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}

export function TfsaRoomCard({ stagger = 3 }: { stagger?: number }) {
  const [tfsa, setTfsa] = useState<WeeklyBrief["tfsa"] | null>(null);

  useEffect(() => {
    let active = true;
    api
      .getWeeklyBrief()
      .then((data) => {
        if (active && data.tfsa) setTfsa(data.tfsa);
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, []);

  if (!tfsa) return null;

  const used = tfsa.estimated_contributions;
  const pct = tfsa.limit > 0 ? Math.min(100, (used / tfsa.limit) * 100) : 0;

  return (
    <section
      className="panel stagger-item rounded-2xl p-5"
      style={{ "--stagger": stagger } as React.CSSProperties}
    >
      <p className="text-[10px] font-medium uppercase tracking-wider text-[var(--muted)]">
        TFSA contribution room
      </p>
      <p className="mt-1 text-2xl font-semibold tabular-nums text-[var(--foreground)]">
        ${tfsa.remaining_room.toLocaleString()}
        <span className="ml-1 text-sm font-normal text-[var(--muted)]">remaining</span>
      </p>
      <div className="mt-3 h-2 overflow-hidden rounded-full bg-[var(--surface)]">
        <div
          className="h-full rounded-full bg-gradient-to-r from-teal-500 to-blue-600 transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
      <p className="mt-2 text-xs text-[var(--muted)]">
        ${used.toLocaleString()} contributed of ${tfsa.limit.toLocaleString()} 2026 limit · verify with CRA
      </p>
      <Link href="/chat" className="link-accent mt-3 inline-block text-xs">
        Ask about TFSA strategy →
      </Link>
    </section>
  );
}
