"use client";

import {
  ArrowDownLeft,
  ArrowDownRight,
  ArrowUpRight,
  BarChart2,
  CreditCard,
  RefreshCw,
  TrendingDown,
  TrendingUp,
  Wallet,
} from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import {
  Area,
  AreaChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";

import { api } from "@/lib/api";
import type { Account, Transaction } from "@/lib/types";
import { getCategoryColor } from "@/lib/types";
import { useChartColors } from "@/lib/chart-theme";
import {
  formatCurrency,
  formatDateShort,
  getCurrentMonthRange,
  getDateRange,
} from "@/lib/utils";

export default function DashboardPage() {
  const chart = useChartColors();
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [recent, setRecent] = useState<Transaction[]>([]);
  const [curMonth, setCurMonth] = useState<Transaction[]>([]);
  const [lastMonth, setLastMonth] = useState<Transaction[]>([]);
  const [daily, setDaily] = useState<{ day: string; spend: number }[]>([]);
  const [loading, setLoading] = useState(true);
  const [apiOk, setApiOk] = useState<boolean | null>(null);

  const fetchAll = useCallback(async () => {
    const { from: curFrom, to: curTo } = getCurrentMonthRange();
    const { from: prevFrom, to: prevTo } = (() => {
      const d = new Date();
      d.setMonth(d.getMonth() - 1);
      return {
        from: new Date(d.getFullYear(), d.getMonth(), 1).toISOString().slice(0, 10),
        to: new Date(d.getFullYear(), d.getMonth() + 1, 0).toISOString().slice(0, 10),
      };
    })();
    const thirtyRange = getDateRange(1);

    const [health, accs, recentList, curList, prevList, thirtyList] = await Promise.all([
      api.health(),
      api.getAccounts(),
      api.getTransactions({ limit: 10 }),
      api.getTransactions({ date_from: curFrom, date_to: curTo, limit: 500 }),
      api.getTransactions({ date_from: prevFrom, date_to: prevTo, limit: 500 }),
      api.getAllTransactions(thirtyRange.from, thirtyRange.to),
    ]);

    // Build daily spend for sparkline
    const dayMap: Record<string, number> = {};
    for (const tx of thirtyList) {
      if (tx.amount < 0)
        dayMap[tx.transaction_date] = (dayMap[tx.transaction_date] ?? 0) + Math.abs(tx.amount);
    }
    const dailyData = Object.entries(dayMap)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([day, spend]) => ({ day: day.slice(5), spend }));

    return { health, accs, recentList, curList, prevList, dailyData };
  }, []);

  useEffect(() => {
    let active = true;
    fetchAll().then(({ health, accs, recentList, curList, prevList, dailyData }) => {
      if (!active) return;
      setApiOk(health.status === "ok");
      setAccounts(accs);
      setRecent(recentList.items);
      setCurMonth(curList.items);
      setLastMonth(prevList.items);
      setDaily(dailyData);
      setLoading(false);
    }).catch(() => { if (active) { setApiOk(false); setLoading(false); } });
    return () => { active = false; };
  }, [fetchAll]);

  const reload = useCallback(() => {
    setLoading(true);
    fetchAll().then(({ health, accs, recentList, curList, prevList, dailyData }) => {
      setApiOk(health.status === "ok");
      setAccounts(accs);
      setRecent(recentList.items);
      setCurMonth(curList.items);
      setLastMonth(prevList.items);
      setDaily(dailyData);
      setLoading(false);
    }).catch(() => { setApiOk(false); setLoading(false); });
  }, [fetchAll]);

  const curSpend = curMonth.filter((t) => t.amount < 0).reduce((s, t) => s + Math.abs(t.amount), 0);
  const curIncome = curMonth.filter((t) => t.amount > 0).reduce((s, t) => s + t.amount, 0);
  const prevSpend = lastMonth.filter((t) => t.amount < 0).reduce((s, t) => s + Math.abs(t.amount), 0);
  const netSavings = curIncome - curSpend;
  const spendChange = prevSpend > 0 ? ((curSpend - prevSpend) / prevSpend) * 100 : null;

  // Top categories this month
  const catMap: Record<string, number> = {};
  for (const tx of curMonth) {
    if (tx.amount < 0) catMap[tx.category] = (catMap[tx.category] ?? 0) + Math.abs(tx.amount);
  }
  const topCategories = Object.entries(catMap)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 6);
  const maxCat = topCategories[0]?.[1] ?? 1;

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.2em] text-[var(--muted)]">Overview</p>
          <h1 className="mt-1 text-3xl font-semibold tracking-tight">
            Good {new Date().getHours() < 12 ? "morning" : new Date().getHours() < 17 ? "afternoon" : "evening"}
          </h1>
          <p className="mt-1 text-sm text-[var(--muted)]">
            {new Date().toLocaleDateString("en-CA", { weekday: "long", month: "long", day: "numeric", year: "numeric" })}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className={["flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium glass",
            apiOk === true ? "text-emerald-400" :
            apiOk === false ? "text-red-400" : "text-[var(--muted)]",
          ].join(" ")}>
            <span className={["h-1.5 w-1.5 rounded-full",
              apiOk === true ? "bg-emerald-400 animate-pulse" : apiOk === false ? "bg-red-400" : "bg-[var(--muted)]",
            ].join(" ")} />
            {apiOk === true ? "Connected" : apiOk === false ? "Offline" : "Checking…"}
          </span>
          <button type="button" onClick={reload} disabled={loading}
            className="btn-ghost flex h-9 w-9 items-center justify-center rounded-xl disabled:opacity-40">
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          </button>
        </div>
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <KpiCard
          icon={<CreditCard size={15} />}
          label="Accounts"
          value={String(accounts.length)}
          sub={accounts.length ? accounts.map((a) => a.name).join(", ") : "No accounts yet"}
          accent="indigo"
          loading={loading}
        />
        <KpiCard
          icon={<TrendingDown size={15} />}
          label="Monthly Spend"
          value={formatCurrency(curSpend)}
          sub={spendChange !== null
            ? `${spendChange > 0 ? "▲" : "▼"} ${Math.abs(spendChange).toFixed(0)}% vs last month`
            : "vs last month"}
          accent={spendChange !== null && spendChange < 0 ? "emerald" : "rose"}
          trend={spendChange}
          loading={loading}
        />
        <KpiCard
          icon={<TrendingUp size={15} />}
          label="Monthly Income"
          value={formatCurrency(curIncome)}
          sub={`${curMonth.filter((t) => t.amount > 0).length} credit transactions`}
          accent="emerald"
          loading={loading}
        />
        <KpiCard
          icon={<Wallet size={15} />}
          label="Net Savings"
          value={formatCurrency(Math.abs(netSavings))}
          sub={netSavings >= 0 ? "Surplus this month" : "Deficit this month"}
          accent={netSavings >= 0 ? "emerald" : "rose"}
          neg={netSavings < 0}
          loading={loading}
        />
      </div>

      {/* Sparkline + quick links */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2 flex flex-col gap-3 glass-elevated rounded-2xl p-6">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-zinc-200">Daily Spending (30 days)</h2>
            <Link href="/analytics" className="text-xs text-indigo-400 hover:text-indigo-300">Full analytics →</Link>
          </div>
          {loading ? (
            <div className="h-[100px] animate-pulse rounded-lg bg-zinc-800" />
          ) : daily.length === 0 ? (
            <p className="py-8 text-center text-sm text-zinc-700">No data yet</p>
          ) : (
            <ResponsiveContainer width="100%" height={100}>
              <AreaChart data={daily}>
                <defs>
                  <linearGradient id="spendGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <Area type="monotone" dataKey="spend" stroke="#6366f1" strokeWidth={2} fill="url(#spendGrad)" dot={false} />
                <Tooltip
                  formatter={(v) => [formatCurrency(v as number), "Spend"]}
                  contentStyle={{ background: chart.tooltipBg, border: `1px solid ${chart.tooltipBorder}`, borderRadius: "8px", fontSize: "11px" }}
                  labelStyle={{ color: chart.axis }}
                />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Quick links */}
        <div className="flex flex-col gap-3">
          {[
            { href: "/analytics", icon: <BarChart2 size={15} />, label: "Analytics", desc: "Charts, trends, merchants" },
            { href: "/transactions", icon: <CreditCard size={15} />, label: "Transactions", desc: "Browse, filter, upload" },
            { href: "/search", icon: <TrendingUp size={15} />, label: "AI Search", desc: "Semantic RAG search" },
          ].map(({ href, icon, label, desc }) => (
            <Link key={href} href={href}
              className="glass flex items-center gap-3 rounded-2xl p-4 transition-all hover:glass-elevated">
              <span className="rounded-lg bg-indigo-500/10 p-2 text-indigo-400">{icon}</span>
              <div>
                <p className="text-sm font-medium text-zinc-200">{label}</p>
                <p className="text-xs text-zinc-600">{desc}</p>
              </div>
              <ArrowUpRight size={14} className="ml-auto text-zinc-700" />
            </Link>
          ))}
        </div>
      </div>

      {/* Bottom grid */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
        {/* Category breakdown */}
        <section className="col-span-1 flex flex-col gap-3 glass-elevated rounded-2xl p-6 lg:col-span-2">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-zinc-200">Spending by Category</h2>
            <span className="text-xs text-zinc-600">This month</span>
          </div>
          {loading ? (
            <ul className="flex flex-col gap-3">{Array.from({ length: 6 }).map((_, i) => (
              <li key={i} className="h-4 animate-pulse rounded bg-zinc-800" />
            ))}</ul>
          ) : topCategories.length === 0 ? (
            <div className="flex flex-col items-center gap-3 py-8 text-center">
              <p className="text-sm text-zinc-600">No spending data yet.</p>
              <Link href="/transactions" className="rounded-lg bg-indigo-600 px-4 py-2 text-xs font-medium text-white hover:bg-indigo-500">
                Upload CSV
              </Link>
            </div>
          ) : (
            <ul className="flex flex-col gap-3">
              {topCategories.map(([cat, total]) => (
                <li key={cat} className="flex flex-col gap-1.5">
                  <div className="flex items-center justify-between text-xs">
                    <span className="flex items-center gap-1.5">
                      <span className="h-2 w-2 rounded-full" style={{ background: getCategoryColor(cat) }} />
                      <span className="text-zinc-300">{cat}</span>
                    </span>
                    <span className="tabular-nums text-zinc-400">{formatCurrency(total)}</span>
                  </div>
                  <div className="h-1.5 w-full overflow-hidden rounded-full bg-zinc-800">
                    <div
                      className="h-full rounded-full transition-all duration-500"
                      style={{ width: `${(total / maxCat) * 100}%`, backgroundColor: getCategoryColor(cat) }}
                    />
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>

        {/* Recent transactions */}
        <section className="col-span-1 flex flex-col gap-3 glass-elevated rounded-2xl p-6 lg:col-span-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-zinc-200">Recent Transactions</h2>
            <Link href="/transactions" className="text-xs text-indigo-400 hover:text-indigo-300">View all →</Link>
          </div>
          {loading ? (
            <ul className="flex flex-col gap-3">{Array.from({ length: 7 }).map((_, i) => (
              <li key={i} className="h-12 animate-pulse rounded-lg bg-zinc-800" />
            ))}</ul>
          ) : recent.length === 0 ? (
            <div className="flex flex-col items-center gap-3 py-8 text-center">
              <p className="text-sm text-zinc-600">No transactions yet.</p>
              <Link href="/transactions" className="rounded-lg bg-indigo-600 px-4 py-2 text-xs font-medium text-white hover:bg-indigo-500">
                Upload CSV
              </Link>
            </div>
          ) : (
            <ul className="flex flex-col divide-y divide-zinc-800/60">
              {recent.map((tx) => (
                <li key={tx.id} className="flex items-center gap-3 py-2.5">
                  <div
                    className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg"
                    style={{ backgroundColor: getCategoryColor(tx.category) + "20" }}
                  >
                    {tx.amount < 0
                      ? <ArrowDownLeft size={14} style={{ color: getCategoryColor(tx.category) }} />
                      : <ArrowUpRight size={14} className="text-emerald-400" />
                    }
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm text-zinc-200">{tx.description}</p>
                    <p className="text-xs text-zinc-500">
                      {tx.category}{tx.merchant ? ` · ${tx.merchant}` : ""} · {formatDateShort(tx.transaction_date)}
                    </p>
                  </div>
                  <span className={["shrink-0 text-sm font-medium tabular-nums",
                    tx.amount < 0 ? "text-red-400" : "text-emerald-400",
                  ].join(" ")}>
                    {tx.amount < 0 ? "-" : "+"}{formatCurrency(tx.amount)}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  );
}

// ── KPI Card ──────────────────────────────────────────────────────────────────

function KpiCard({ icon, label, value, sub, accent, trend, neg, loading }: {
  icon: React.ReactNode; label: string; value: string; sub: string;
  accent: "indigo" | "sky" | "rose" | "emerald"; trend?: number | null; neg?: boolean; loading?: boolean;
}) {
  const cls: Record<string, string> = {
    indigo: "bg-indigo-500/10 text-indigo-400",
    sky: "bg-sky-500/10 text-sky-400",
    rose: "bg-rose-500/10 text-rose-400",
    emerald: "bg-emerald-500/10 text-emerald-400",
  };
  return (
    <div className="glass-elevated flex flex-col gap-3 rounded-2xl p-5 glow-accent">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-zinc-500">{label}</span>
        <span className={`rounded-lg p-1.5 ${cls[accent]}`}>{icon}</span>
      </div>
      {loading ? (
        <div className="h-8 animate-pulse rounded bg-zinc-800" />
      ) : (
        <p className={["text-2xl font-semibold tabular-nums", neg ? "text-rose-400" : "text-zinc-50"].join(" ")}>
          {neg ? "−" : ""}{value}
        </p>
      )}
      <p className="flex items-center gap-1 truncate text-xs text-zinc-600">
        {trend !== null && trend !== undefined && (
          trend < 0
            ? <ArrowDownRight size={11} className="text-emerald-500" />
            : <ArrowUpRight size={11} className="text-rose-500" />
        )}
        {sub}
      </p>
    </div>
  );
}
