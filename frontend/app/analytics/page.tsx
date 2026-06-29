"use client";

import {
  ArrowDownRight,
  ArrowUpRight,
  BarChart2,
  RefreshCw,
  ShoppingBag,
  TrendingDown,
  TrendingUp,
  Wallet,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { PageHeader } from "@/components/ui/PageHeader";
import { useAuthReady } from "@/hooks/useAuthReady";
import { api } from "@/lib/api";
import type { Transaction } from "@/lib/types";
import { getCategoryColor } from "@/lib/types";
import { useChartColors } from "@/lib/chart-theme";
import {
  exportToCsv,
  formatCurrency,
  getDateRange,
  getYearToDateRange,
  monthLabel,
} from "@/lib/utils";

type Period = "3M" | "6M" | "YTD" | "12M";

const PERIODS: { label: Period; months?: number; ytd?: boolean }[] = [
  { label: "3M", months: 3 },
  { label: "6M", months: 6 },
  { label: "YTD", ytd: true },
  { label: "12M", months: 12 },
];

interface MonthRow {
  month: string;
  label: string;
  income: number;
  spend: number;
  net: number;
  count: number;
}

interface CategoryRow {
  category: string;
  total: number;
  count: number;
  pct: number;
}

interface MerchantRow {
  merchant: string;
  total: number;
  count: number;
}

interface DayRow {
  day: string;
  spend: number;
}

function processTransactions(txs: Transaction[]) {
  // Monthly buckets
  const monthMap: Record<string, MonthRow> = {};
  // Category buckets
  const catMap: Record<string, { total: number; count: number }> = {};
  // Merchant buckets
  const merMap: Record<string, { total: number; count: number }> = {};
  // Daily spend (last 30 days)
  const dayMap: Record<string, number> = {};

  const thirtyDaysAgo = new Date();
  thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);

  for (const tx of txs) {
    const ym = tx.transaction_date.slice(0, 7);
    if (!monthMap[ym])
      monthMap[ym] = { month: ym, label: monthLabel(ym), income: 0, spend: 0, net: 0, count: 0 };
    monthMap[ym].count += 1;
    if (tx.amount < 0) {
      const abs = Math.abs(tx.amount);
      monthMap[ym].spend += abs;
      catMap[tx.category] = catMap[tx.category] ?? { total: 0, count: 0 };
      catMap[tx.category].total += abs;
      catMap[tx.category].count += 1;
      if (tx.merchant) {
        merMap[tx.merchant] = merMap[tx.merchant] ?? { total: 0, count: 0 };
        merMap[tx.merchant].total += abs;
        merMap[tx.merchant].count += 1;
      }
      // daily
      if (new Date(tx.transaction_date) >= thirtyDaysAgo) {
        dayMap[tx.transaction_date] = (dayMap[tx.transaction_date] ?? 0) + abs;
      }
    } else {
      monthMap[ym].income += tx.amount;
    }
    monthMap[ym].net = monthMap[ym].income - monthMap[ym].spend;
  }

  const months = Object.values(monthMap).sort((a, b) => a.month.localeCompare(b.month));

  const totalSpend = Object.values(catMap).reduce((s, c) => s + c.total, 0);
  const categories: CategoryRow[] = Object.entries(catMap)
    .map(([cat, { total, count }]) => ({
      category: cat,
      total,
      count,
      pct: totalSpend > 0 ? (total / totalSpend) * 100 : 0,
    }))
    .sort((a, b) => b.total - a.total);

  const merchants: MerchantRow[] = Object.entries(merMap)
    .map(([m, { total, count }]) => ({ merchant: m, total, count }))
    .sort((a, b) => b.total - a.total)
    .slice(0, 10);

  // Daily spend for last 30 days sorted
  const days: DayRow[] = Object.entries(dayMap)
    .map(([day, spend]) => ({ day, spend }))
    .sort((a, b) => a.day.localeCompare(b.day));

  return { months, categories, merchants, days };
}

// ── Custom Tooltip ─────────────────────────────────────────────────────────

function ChartTooltip({ active, payload, label }: {
  active?: boolean; payload?: { name: string; value: number; color: string }[]; label?: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-xl border border-zinc-700 bg-zinc-900 p-3 shadow-xl text-xs text-zinc-300">
      <p className="mb-1.5 font-medium">{label}</p>
      {payload.map((p) => (
        <div key={p.name} className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full" style={{ background: p.color }} />
          <span className="text-zinc-400 capitalize">{p.name}</span>
          <span className="ml-auto pl-4 font-medium tabular-nums">
            {formatCurrency(p.value)}
          </span>
        </div>
      ))}
    </div>
  );
}

// ── Page ───────────────────────────────────────────────────────────────────

export default function AnalyticsPage() {
  const authReady = useAuthReady();
  const [period, setPeriod] = useState<Period>("6M");
  const [txs, setTxs] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const chart = useChartColors();

  const fetchData = useCallback((p: Period) => {
    const range =
      p === "YTD"
        ? getYearToDateRange()
        : getDateRange(p === "3M" ? 3 : p === "6M" ? 6 : 12);
    return api.getAllTransactions(range.from, range.to);
  }, []);

  useEffect(() => {
    if (!authReady) return;
    let active = true;
    fetchData(period).then((data) => {
      if (active) { setTxs(data); setLoading(false); }
    }).catch(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [authReady, fetchData, period]);

  const handlePeriod = (p: Period) => {
    setPeriod(p);
    setLoading(true);
  };

  const { months, categories, merchants, days } = processTransactions(txs);

  const totalSpend = txs.filter((t) => t.amount < 0).reduce((s, t) => s + Math.abs(t.amount), 0);
  const totalIncome = txs.filter((t) => t.amount > 0).reduce((s, t) => s + t.amount, 0);
  const netSavings = totalIncome - totalSpend;
  const avgMonthlySpend = months.length ? totalSpend / months.length : 0;

  const handleExport = () => {
    exportToCsv("transactions-export.csv", [
      ["Date", "Description", "Amount", "Category", "Merchant", "Notes"],
      ...txs.map((t) => [
        t.transaction_date,
        t.description,
        String(t.amount),
        t.category,
        t.merchant ?? "",
        t.notes ?? "",
      ]),
    ]);
  };

  return (
    <div className="page-container">
      <PageHeader
        eyebrow="Insights"
        title="Analytics"
        subtitle={`${txs.length.toLocaleString()} transactions · ${period} view`}
        actions={
          <>
            <div className="flex panel rounded-xl p-0.5">
              {PERIODS.map(({ label }) => (
                <button
                  key={label}
                  type="button"
                  onClick={() => handlePeriod(label)}
                  className={[
                    "rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
                    period === label
                      ? "bg-indigo-600 text-white"
                      : "text-[var(--muted)] hover:text-[var(--foreground)]",
                  ].join(" ")}
                >
                  {label}
                </button>
              ))}
            </div>
            <button
              type="button"
              onClick={handleExport}
              className="btn-ghost flex items-center gap-1.5 rounded-xl px-3 py-2 text-xs"
            >
              Export CSV
            </button>
            <button
              type="button"
              onClick={() => { setLoading(true); fetchData(period).then((d) => { setTxs(d); setLoading(false); }); }}
              disabled={loading}
              className="btn-ghost flex h-9 w-9 items-center justify-center rounded-xl disabled:opacity-40"
            >
              <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
            </button>
          </>
        }
      />

      {/* KPI row */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <KpiCard icon={<TrendingDown size={15} />} label="Total Spend" value={formatCurrency(totalSpend)} accent="rose" sub={`Avg ${formatCurrency(avgMonthlySpend)}/mo`} />
        <KpiCard icon={<TrendingUp size={15} />} label="Total Income" value={formatCurrency(totalIncome)} accent="emerald" sub={`${txs.filter(t => t.amount > 0).length} credits`} />
        <KpiCard icon={<Wallet size={15} />} label="Net Savings" value={formatCurrency(Math.abs(netSavings))} accent={netSavings >= 0 ? "emerald" : "rose"} sub={netSavings >= 0 ? "Surplus" : "Deficit"} neg={netSavings < 0} />
        <KpiCard icon={<BarChart2 size={15} />} label="Transactions" value={txs.length.toLocaleString()} accent="indigo" sub={`${months.length} months`} />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Monthly bar chart */}
        <ChartCard title="Income vs Spending" subtitle="By month" className="lg:col-span-2">
          {loading ? (
            <Skeleton h={240} />
          ) : months.length === 0 ? (
            <Empty />
          ) : (
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={months} barGap={3} barCategoryGap="35%">
                <CartesianGrid strokeDasharray="3 3" stroke={chart.grid} vertical={false} />
                <XAxis dataKey="label" tick={{ fill: chart.axis, fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: chart.axis, fontSize: 11 }} axisLine={false} tickLine={false} tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}k`} width={44} />
                <Tooltip content={<ChartTooltip />} cursor={{ fill: "#7f7f7f10" }} />
                <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: "11px", color: chart.axis }} />
                <Bar dataKey="income" name="income" fill="#10b981" radius={[4, 4, 0, 0]} />
                <Bar dataKey="spend" name="spend" fill="#f43f5e" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </ChartCard>

        {/* Category donut */}
        <ChartCard title="Spending by Category" subtitle="Current period">
          {loading ? (
            <Skeleton h={240} />
          ) : categories.length === 0 ? (
            <Empty />
          ) : (
            <div className="flex flex-col gap-3">
              <ResponsiveContainer width="100%" height={160}>
                <PieChart>
                  <Pie
                    data={categories}
                    dataKey="total"
                    nameKey="category"
                    cx="50%"
                    cy="50%"
                    innerRadius="55%"
                    outerRadius="80%"
                    paddingAngle={2}
                  >
                    {categories.map((c) => (
                      <Cell key={c.category} fill={getCategoryColor(c.category)} />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(v) => formatCurrency(v as number)}
                    contentStyle={{ background: chart.tooltipBg, border: `1px solid ${chart.tooltipBorder}`, borderRadius: "8px", fontSize: "12px" }}
                  />
                </PieChart>
              </ResponsiveContainer>
              <ul className="flex flex-col gap-1.5">
                {categories.slice(0, 6).map((c) => (
                  <li key={c.category} className="flex items-center gap-2 text-xs">
                    <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: getCategoryColor(c.category) }} />
                    <span className="flex-1 text-zinc-400 truncate">{c.category}</span>
                    <span className="tabular-nums text-zinc-300">{formatCurrency(c.total)}</span>
                    <span className="w-8 text-right text-zinc-600">{c.pct.toFixed(0)}%</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </ChartCard>
      </div>

      {/* Daily spend + merchants */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Daily spend line */}
        <ChartCard title="Daily Spending" subtitle="Last 30 days" className="lg:col-span-2">
          {loading ? (
            <Skeleton h={180} />
          ) : days.length === 0 ? (
            <Empty />
          ) : (
            <ResponsiveContainer width="100%" height={180}>
              <LineChart data={days}>
                <CartesianGrid strokeDasharray="3 3" stroke={chart.grid} vertical={false} />
                <XAxis dataKey="day" tick={{ fill: chart.axis, fontSize: 10 }} axisLine={false} tickLine={false}
                  tickFormatter={(v: string) => v.slice(5)} interval="preserveStartEnd" />
                <YAxis tick={{ fill: chart.axis, fontSize: 10 }} axisLine={false} tickLine={false}
                  tickFormatter={(v: number) => `$${v.toFixed(0)}`} width={44} />
                <Tooltip
                  formatter={(v) => [formatCurrency(v as number), "Spend"]}
                  contentStyle={{ background: chart.tooltipBg, border: `1px solid ${chart.tooltipBorder}`, borderRadius: "8px", fontSize: "12px" }}
                />
                <Line type="monotone" dataKey="spend" stroke="#6366f1" strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </ChartCard>

        {/* Top merchants */}
        <ChartCard title="Top Merchants" subtitle="By spend">
          {loading ? (
            <Skeleton h={180} />
          ) : merchants.length === 0 ? (
            <Empty text="No merchant data" />
          ) : (
            <ul className="flex flex-col gap-2.5">
              {merchants.slice(0, 7).map((m, i) => {
                const max = merchants[0]?.total ?? 1;
                return (
                  <li key={m.merchant} className="flex items-center gap-3">
                    <span className="w-4 text-right text-xs font-medium text-zinc-700">{i + 1}</span>
                    <div className="flex-1">
                      <div className="flex items-center justify-between text-xs mb-1">
                        <span className="truncate text-zinc-300">{m.merchant}</span>
                        <span className="pl-2 tabular-nums text-zinc-400">{formatCurrency(m.total)}</span>
                      </div>
                      <div className="h-1 w-full overflow-hidden rounded-full bg-zinc-800">
                        <div
                          className="h-full rounded-full bg-indigo-500/70 transition-all duration-500"
                          style={{ width: `${(m.total / max) * 100}%` }}
                        />
                      </div>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </ChartCard>
      </div>

      {/* Monthly summary table */}
      <section className="panel rounded-2xl p-5">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-zinc-200">Monthly Breakdown</h2>
          <span className="text-xs text-zinc-600">{months.length} months</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-zinc-800">
                {["Month", "Income", "Spending", "Net", "Transactions"].map((h) => (
                  <th key={h} className="pb-3 text-left text-xs font-medium text-zinc-500">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/50">
              {loading
                ? Array.from({ length: 4 }).map((_, i) => (
                    <tr key={i}>
                      {Array.from({ length: 5 }).map((_, j) => (
                        <td key={j} className="py-3 pr-6">
                          <div className="h-3.5 shimmer rounded" />
                        </td>
                      ))}
                    </tr>
                  ))
                : [...months].reverse().map((m) => (
                    <tr key={m.month} className="hover:bg-zinc-800/30">
                      <td className="py-3 pr-6 font-medium text-zinc-300">{m.label}</td>
                      <td className="py-3 pr-6 tabular-nums text-emerald-400">{formatCurrency(m.income)}</td>
                      <td className="py-3 pr-6 tabular-nums text-rose-400">{formatCurrency(m.spend)}</td>
                      <td className={["py-3 pr-6 tabular-nums font-medium", m.net >= 0 ? "text-emerald-400" : "text-rose-400"].join(" ")}>
                        <span className="flex items-center gap-1">
                          {m.net >= 0 ? <ArrowUpRight size={12} /> : <ArrowDownRight size={12} />}
                          {formatCurrency(Math.abs(m.net))}
                        </span>
                      </td>
                      <td className="py-3 text-zinc-500">{m.count}</td>
                    </tr>
                  ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Category detail table */}
      <section className="panel rounded-2xl p-5">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-zinc-200">Category Detail</h2>
          <ShoppingBag size={14} className="text-zinc-600" />
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-zinc-800">
                {["Category", "Total Spent", "Transactions", "% of Spend"].map((h) => (
                  <th key={h} className="pb-3 text-left text-xs font-medium text-zinc-500">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/50">
              {loading
                ? Array.from({ length: 5 }).map((_, i) => (
                    <tr key={i}>{Array.from({ length: 4 }).map((_, j) => (
                      <td key={j} className="py-3 pr-6"><div className="h-3.5 shimmer rounded" /></td>
                    ))}</tr>
                  ))
                : categories.map((c) => (
                    <tr key={c.category} className="hover:bg-zinc-800/30">
                      <td className="py-3 pr-6">
                        <div className="flex items-center gap-2">
                          <span className="h-2 w-2 rounded-full" style={{ background: getCategoryColor(c.category) }} />
                          <span className="text-zinc-300">{c.category}</span>
                        </div>
                      </td>
                      <td className="py-3 pr-6 tabular-nums text-zinc-200">{formatCurrency(c.total)}</td>
                      <td className="py-3 pr-6 text-zinc-500">{c.count}</td>
                      <td className="py-3">
                        <div className="flex items-center gap-2">
                          <div className="h-1.5 w-24 overflow-hidden rounded-full bg-zinc-800">
                            <div
                              className="h-full rounded-full transition-all"
                              style={{ width: `${c.pct}%`, background: getCategoryColor(c.category) }}
                            />
                          </div>
                          <span className="text-xs text-zinc-500">{c.pct.toFixed(1)}%</span>
                        </div>
                      </td>
                    </tr>
                  ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────────

function KpiCard({ icon, label, value, accent, sub, neg }: {
  icon: React.ReactNode; label: string; value: string;
  accent: "rose" | "emerald" | "indigo"; sub: string; neg?: boolean;
}) {
  const accentCls: Record<string, string> = {
    rose: "kpi-accent-rose",
    emerald: "kpi-accent-emerald",
    indigo: "kpi-accent-indigo",
  };
  return (
    <div className={`kpi-card panel-interactive ${accentCls[accent]}`}>
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium uppercase tracking-wider text-[var(--muted)]">{label}</span>
        <span className="kpi-icon">{icon}</span>
      </div>
      <p className={["text-2xl font-semibold tabular-nums tracking-tight", neg ? "text-rose-400" : ""].join(" ")}>
        {neg ? "−" : ""}{value}
      </p>
      <p className="truncate text-xs text-[var(--muted)]">{sub}</p>
    </div>
  );
}

function ChartCard({ title, subtitle, children, className }: {
  title: string; subtitle?: string; children: React.ReactNode; className?: string;
}) {
  return (
    <div className={["panel flex flex-col gap-4 rounded-2xl p-5", className].filter(Boolean).join(" ")}>
      <div className="flex items-center justify-between">
        <h2 className="section-title">{title}</h2>
        {subtitle && <span className="text-xs text-[var(--muted)]">{subtitle}</span>}
      </div>
      {children}
    </div>
  );
}

function Skeleton({ h }: { h: number }) {
  return <div className="shimmer rounded-lg" style={{ height: h }} />;
}

function Empty({ text = "No data for this period" }: { text?: string }) {
  return (
    <div className="flex items-center justify-center py-12 text-sm text-zinc-700">{text}</div>
  );
}
