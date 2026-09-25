"use client";

import {
  ArrowDownLeft,
  ArrowUpRight,
  BarChart2,
  CreditCard,
  TrendingDown,
  TrendingUp,
  Wallet,
} from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState, type CSSProperties } from "react";
import {
  Area,
  AreaChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";

import { KpiCard } from "@/components/ui/KpiCard";
import { OnboardingBanner } from "@/components/OnboardingBanner";
import { DataStatusBanner } from "@/components/DataStatusBanner";
import { BudgetsPanel } from "@/components/BudgetsPanel";
import { FinancialGoalsPanel } from "@/components/FinancialGoalsPanel";
import {
  SpendAlertsPanel,
  TfsaRoomCard,
  WeeklyBriefPanel,
} from "@/components/dashboard/InsightsPanels";
import { api } from "@/lib/api";
import { chatUrl, promptFromInsightAction } from "@/lib/chat-url";
import { useAuthReady } from "@/hooks/useAuthReady";
import type { Account, InsightCard, Transaction, WeeklyBrief } from "@/lib/types";
import { getCategoryColor } from "@/lib/types";
import { useChartColors } from "@/lib/chart-theme";
import { formatCurrency, formatDateShort } from "@/lib/utils";

export default function DashboardPage() {
  const chart = useChartColors();
  const authReady = useAuthReady();
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [recent, setRecent] = useState<Transaction[]>([]);
  const [daily, setDaily] = useState<{ day: string; spend: number }[]>([]);
  const [loading, setLoading] = useState(true);
  const [dataError, setDataError] = useState<string | null>(null);
  const [insightCards, setInsightCards] = useState<InsightCard[]>([]);
  const [weeklyBrief, setWeeklyBrief] = useState<WeeklyBrief | null>(null);
  const [curSpend, setCurSpend] = useState(0);
  const [curIncome, setCurIncome] = useState(0);
  const [netSavings, setNetSavings] = useState(0);
  const [spendChange, setSpendChange] = useState<number | null>(null);
  const [creditCount, setCreditCount] = useState(0);
  const [topCategories, setTopCategories] = useState<[string, number][]>([]);

  const fetchAll = useCallback(async () => {
    try {
      const data = await api.getDashboard();
      const cats: [string, number][] = data.top_categories.map((c) => [c.category, c.amount]);
      return {
        accounts: data.accounts,
        recent: data.recent,
        daily: data.daily,
        dataError: null as string | null,
        insightCards: data.insight_cards,
        weeklyBrief: data.weekly_brief,
        curSpend: data.kpis.cur_spend,
        curIncome: data.kpis.cur_income,
        netSavings: data.kpis.net_savings,
        spendChange: data.kpis.spend_change_pct,
        creditCount: data.kpis.credit_count,
        topCategories: cats,
      };
    } catch (err) {
      const raw = err instanceof Error ? err.message : "Failed to load data";
      const msg = raw.replace(/^API \d+:\s*/i, "").slice(0, 220);
      return {
        accounts: [] as Account[],
        recent: [] as Transaction[],
        daily: [] as { day: string; spend: number }[],
        dataError: msg || "We couldn't load your finances right now. Please try again.",
        insightCards: [] as InsightCard[],
        weeklyBrief: null as WeeklyBrief | null,
        curSpend: 0,
        curIncome: 0,
        netSavings: 0,
        spendChange: null as number | null,
        creditCount: 0,
        topCategories: [] as [string, number][],
      };
    }
  }, []);

  const applyPayload = useCallback((payload: Awaited<ReturnType<typeof fetchAll>>) => {
    setDataError(payload.dataError);
    setAccounts(payload.accounts);
    setRecent(payload.recent);
    setDaily(payload.daily);
    setInsightCards(payload.insightCards);
    setWeeklyBrief(payload.weeklyBrief);
    setCurSpend(payload.curSpend);
    setCurIncome(payload.curIncome);
    setNetSavings(payload.netSavings);
    setSpendChange(payload.spendChange);
    setCreditCount(payload.creditCount);
    setTopCategories(payload.topCategories);
    setLoading(false);
  }, []);

  const reload = useCallback(() => {
    setLoading(true);
    fetchAll().then(applyPayload).catch(() => setLoading(false));
  }, [fetchAll, applyPayload]);

  useEffect(() => {
    if (!authReady) return;
    let active = true;
    fetchAll()
      .then((payload) => {
        if (!active) return;
        applyPayload(payload);
      })
      .catch(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [authReady, fetchAll, applyPayload]);

  const maxCat = topCategories[0]?.[1] ?? 1;
  const greeting =
    new Date().getHours() < 12
      ? "morning"
      : new Date().getHours() < 17
        ? "afternoon"
        : "evening";

  return (
    <div className="page-container gap-8">
      <header
        className="page-header stagger-item"
        style={{ "--stagger": 0 } as CSSProperties}
      >
        <div className="min-w-0">
          <p className="eyebrow">Overview</p>
          <h1 className="hero-title mt-1">
            Good <span className="text-gradient">{greeting}</span>
          </h1>
          <p className="page-subtitle mt-1.5">
            {new Date().toLocaleDateString("en-CA", {
              weekday: "long",
              month: "long",
              day: "numeric",
              year: "numeric",
            })}
          </p>
        </div>
      </header>

      <DataStatusBanner error={dataError} onRetry={reload} loading={loading} />

      {!loading && accounts.length === 0 && !dataError && <OnboardingBanner />}

      {accounts.length > 0 && !dataError && (
        <>
          <WeeklyBriefPanel stagger={1} initial={weeklyBrief} />
          <SpendAlertsPanel stagger={2} initial={weeklyBrief?.alerts ?? []} />
        </>
      )}

      {insightCards.length > 0 && (
        <section className="grid gap-3 sm:grid-cols-2">
          {insightCards.map((card) => (
            <div
              key={card.id}
              className={[
                "panel rounded-xl p-4",
                card.severity === "warning" && "border-amber-500/30",
                card.severity === "success" && "border-emerald-500/30",
              ].filter(Boolean).join(" ")}
            >
              <p className="text-sm font-medium text-[var(--foreground)]">{card.title}</p>
              <p className="mt-1 text-xs text-[var(--muted)]">{card.body}</p>
              {card.action && (
                <Link
                  href={chatUrl(promptFromInsightAction(card.action))}
                  className="link-accent mt-2 inline-block text-xs"
                >
                  {card.action}
                </Link>
              )}
            </div>
          ))}
        </section>
      )}

      <FinancialGoalsPanel stagger={3} />

      <BudgetsPanel stagger={4} />

      {accounts.length > 0 && !dataError && (
        <TfsaRoomCard stagger={5} initial={weeklyBrief?.tfsa ?? null} />
      )}

      {/* KPI row */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <KpiCard
          icon={<CreditCard size={15} />}
          label="Accounts"
          value={String(accounts.length)}
          sub={accounts.length ? accounts.map((a) => a.name).join(", ") : "No accounts yet"}
          accent="teal"
          loading={loading}
          stagger={1}
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
          stagger={2}
        />
        <KpiCard
          icon={<TrendingUp size={15} />}
          label="Monthly Income"
          value={formatCurrency(curIncome)}
          sub={`${creditCount} credit transactions`}
          accent="emerald"
          loading={loading}
          stagger={3}
        />
        <KpiCard
          icon={<Wallet size={15} />}
          label="Net Savings"
          value={formatCurrency(Math.abs(netSavings))}
          sub={netSavings >= 0 ? "Surplus this month" : "Deficit this month"}
          accent={netSavings >= 0 ? "emerald" : "rose"}
          neg={netSavings < 0}
          loading={loading}
          stagger={4}
        />
      </div>

      {/* Sparkline + quick links */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div
          className="panel lg:col-span-2 flex flex-col gap-3 rounded-2xl p-6 stagger-item"
          style={{ "--stagger": 5 } as CSSProperties}
        >
          <div className="flex items-center justify-between">
            <h2 className="section-title">Daily Spending (30 days)</h2>
            <Link href="/analytics" className="link-accent text-xs">
              Full analytics →
            </Link>
          </div>
          {loading ? (
            <div className="shimmer h-[100px] rounded-xl" />
          ) : daily.length === 0 ? (
            <p className="py-8 text-center text-sm text-[var(--muted)]">No data yet</p>
          ) : (
            <ResponsiveContainer width="100%" height={100}>
              <AreaChart data={daily}>
                <defs>
                  <linearGradient id="spendGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#14b8a6" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#14b8a6" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <Area type="monotone" dataKey="spend" stroke="#14b8a6" strokeWidth={2} fill="url(#spendGrad)" dot={false} />
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
            { href: "/search", icon: <TrendingUp size={15} />, label: "Search", desc: "Semantic transaction search" },
          ].map(({ href, icon, label, desc }, i) => (
            <Link
              key={href}
              href={href}
              className="link-card stagger-item"
              style={{ "--stagger": 6 + i } as CSSProperties}
            >
              <span className="link-card-icon">{icon}</span>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-[var(--foreground)]">{label}</p>
                <p className="text-xs text-[var(--muted)]">{desc}</p>
              </div>
              <ArrowUpRight size={14} className="shrink-0 text-[var(--muted)]" />
            </Link>
          ))}
        </div>
      </div>

      {/* Bottom grid */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
        {/* Category breakdown */}
        <section
          className="panel col-span-1 flex flex-col gap-3 rounded-2xl p-6 lg:col-span-2 stagger-item"
          style={{ "--stagger": 9 } as CSSProperties}
        >
          <div className="flex items-center justify-between">
            <h2 className="section-title">Spending by Category</h2>
            <span className="text-xs text-[var(--muted)]">This month</span>
          </div>
          {loading ? (
            <ul className="flex flex-col gap-3">{Array.from({ length: 6 }).map((_, i) => (
              <li key={i} className="shimmer h-4 rounded" />
            ))}</ul>
          ) : topCategories.length === 0 ? (
            <div className="flex flex-col items-center gap-3 py-8 text-center">
              <p className="text-sm text-[var(--muted)]">No spending data yet.</p>
              <Link href="/transactions" className="btn-primary rounded-xl px-4 py-2 text-xs font-medium">
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
                      <span className="text-[var(--foreground)]">{cat}</span>
                    </span>
                    <span className="tabular-nums text-[var(--muted)]">{formatCurrency(total)}</span>
                  </div>
                  <div className="h-1.5 w-full overflow-hidden rounded-full bg-[var(--surface)]">
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
        <section
          className="panel col-span-1 flex flex-col gap-3 rounded-2xl p-6 lg:col-span-3 stagger-item"
          style={{ "--stagger": 10 } as CSSProperties}
        >
          <div className="flex items-center justify-between">
            <h2 className="section-title">Recent Transactions</h2>
            <Link href="/transactions" className="link-accent text-xs">
              View all →
            </Link>
          </div>
          {loading ? (
            <ul className="flex flex-col gap-3">{Array.from({ length: 7 }).map((_, i) => (
              <li key={i} className="shimmer h-12 rounded-xl" />
            ))}</ul>
          ) : recent.length === 0 ? (
            <div className="flex flex-col items-center gap-3 py-8 text-center">
              <p className="text-sm text-[var(--muted)]">No transactions yet.</p>
              <Link href="/transactions" className="btn-primary rounded-xl px-4 py-2 text-xs font-medium">
                Upload CSV
              </Link>
            </div>
          ) : (
            <ul className="flex flex-col divide-y divide-[var(--border)]">
              {recent.map((tx) => (
                <li
                  key={tx.id}
                  className="group flex items-center gap-3 py-2.5 transition-colors hover:bg-[var(--accent-soft)]/30 rounded-lg px-1 -mx-1"
                >
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
                    <p className="truncate text-sm text-[var(--foreground)]">{tx.description}</p>
                    <p className="text-xs text-[var(--muted)]">
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
