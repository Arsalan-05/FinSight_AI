"use client";

import { LineChart, Loader2 } from "lucide-react";
import { useState, type CSSProperties, type FormEvent } from "react";

import { PageHeader } from "@/components/ui/PageHeader";
import { api } from "@/lib/api";
import type { ForecastResult } from "@/lib/types";
import { formatCurrency } from "@/lib/utils";

function num(v: FormDataEntryValue | null, fallback = 0): number {
  const n = Number(v);
  return Number.isFinite(n) ? n : fallback;
}

export default function ForecastPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ForecastResult | null>(null);

  const onSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    const fd = new FormData(e.currentTarget);
    try {
      const data = await api.runForecast({
        starting_balance: num(fd.get("starting_balance"), 5000),
        monthly_income_mean: num(fd.get("monthly_income_mean"), 3500),
        monthly_income_std: num(fd.get("monthly_income_std"), 200),
        monthly_expense_mean: num(fd.get("monthly_expense_mean"), 2800),
        monthly_expense_std: num(fd.get("monthly_expense_std"), 250),
        months: Math.round(num(fd.get("months"), 12)),
        n_sims: Math.round(num(fd.get("n_sims"), 2000)),
        seed: fd.get("seed") === "" ? null : Math.round(num(fd.get("seed"))),
        ruin_threshold: num(fd.get("ruin_threshold"), 0),
      });
      setResult(data);
    } catch (err) {
      setResult(null);
      setError(err instanceof Error ? err.message : "Forecast failed");
    } finally {
      setLoading(false);
    }
  };

  const bands = result?.bands_by_month ?? [];
  const minP = bands.length ? Math.min(...bands.map((b) => b.p10)) : 0;
  const maxP = bands.length ? Math.max(...bands.map((b) => b.p90)) : 1;
  const span = Math.max(maxP - minP, 1);

  const toPct = (v: number) => `${((v - minP) / span) * 100}%`;

  return (
    <div className="page-container gap-6">
      <PageHeader
        eyebrow="Monte Carlo"
        title="Cash"
        titleAccent="Forecast"
        subtitle="P10 / P50 / P90 ending-balance bands from simulated income and expenses."
      />

      <div className="grid gap-6 lg:grid-cols-5">
        <form
          onSubmit={(e) => void onSubmit(e)}
          className="panel flex flex-col gap-4 rounded-2xl p-5 lg:col-span-2 stagger-item"
          style={{ "--stagger": 1 } as CSSProperties}
        >
          <h2 className="section-title">Assumptions</h2>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2">
            <label className="text-xs text-[var(--muted)]">
              Starting balance
              <input name="starting_balance" type="number" defaultValue={5000} className="input-field mt-1" />
            </label>
            <label className="text-xs text-[var(--muted)]">
              Months
              <input name="months" type="number" min={1} max={120} defaultValue={12} className="input-field mt-1" />
            </label>
            <label className="text-xs text-[var(--muted)]">
              Income mean / mo
              <input name="monthly_income_mean" type="number" defaultValue={3500} className="input-field mt-1" />
            </label>
            <label className="text-xs text-[var(--muted)]">
              Income std
              <input name="monthly_income_std" type="number" min={0} defaultValue={200} className="input-field mt-1" />
            </label>
            <label className="text-xs text-[var(--muted)]">
              Expense mean / mo
              <input name="monthly_expense_mean" type="number" defaultValue={2800} className="input-field mt-1" />
            </label>
            <label className="text-xs text-[var(--muted)]">
              Expense std
              <input name="monthly_expense_std" type="number" min={0} defaultValue={250} className="input-field mt-1" />
            </label>
            <label className="text-xs text-[var(--muted)]">
              Simulations
              <input name="n_sims" type="number" min={100} max={20000} defaultValue={2000} className="input-field mt-1" />
            </label>
            <label className="text-xs text-[var(--muted)]">
              Ruin threshold
              <input name="ruin_threshold" type="number" defaultValue={0} className="input-field mt-1" />
            </label>
            <label className="text-xs text-[var(--muted)] sm:col-span-2">
              Seed (optional)
              <input name="seed" type="number" placeholder="reproducible" className="input-field mt-1" />
            </label>
          </div>
          <button
            type="submit"
            disabled={loading}
            className="btn-primary inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm"
          >
            {loading ? <Loader2 size={14} className="animate-spin" /> : <LineChart size={14} />}
            Run forecast
          </button>
        </form>

        <div
          className="panel rounded-2xl p-5 lg:col-span-3 stagger-item"
          style={{ "--stagger": 2 } as CSSProperties}
        >
          <h2 className="section-title">P10 / P50 / P90 bands</h2>

          {error && (
            <p className="mt-4 rounded-xl border border-rose-500/25 bg-rose-500/5 px-4 py-3 text-sm text-rose-400">
              {error}
            </p>
          )}

          {loading && (
            <div className="mt-4 space-y-3">
              {Array.from({ length: 8 }).map((_, i) => (
                <div key={i} className="shimmer h-6 rounded-lg" />
              ))}
            </div>
          )}

          {!loading && !result && !error && (
            <div className="mt-10 flex flex-col items-center gap-3 text-center">
              <LineChart size={28} className="text-[var(--muted)]" />
              <p className="text-sm text-[var(--muted)]">
                Run a forecast to see monthly confidence bands.
              </p>
            </div>
          )}

          {!loading && result && (
            <div className="mt-4 flex flex-col gap-5">
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                {[
                  { label: "P10 end", value: result.ending_balance.p10 },
                  { label: "P50 end", value: result.ending_balance.p50 },
                  { label: "P90 end", value: result.ending_balance.p90 },
                  { label: "P(ruin)", value: result.p_ruin, pct: true as const },
                ].map((k) => (
                  <div
                    key={k.label}
                    className="rounded-xl border border-[var(--border)] bg-[var(--surface)] px-3 py-2.5"
                  >
                    <p className="text-[10px] uppercase tracking-wider text-[var(--muted)]">{k.label}</p>
                    <p className="mt-0.5 text-sm font-semibold tabular-nums text-[var(--foreground)]">
                      {"pct" in k && k.pct
                        ? `${(k.value * 100).toFixed(1)}%`
                        : formatCurrency(k.value)}
                    </p>
                  </div>
                ))}
              </div>

              <div className="flex flex-col gap-2.5">
                <div className="mb-1 flex flex-wrap gap-3 text-[10px] text-[var(--muted)]">
                  <span className="inline-flex items-center gap-1.5">
                    <span className="h-2 w-6 rounded-full bg-[rgba(20,184,166,0.25)]" />
                    P10–P90 range
                  </span>
                  <span className="inline-flex items-center gap-1.5">
                    <span className="h-2 w-0.5 rounded bg-[var(--accent)]" />
                    P50 median
                  </span>
                </div>
                {bands.map((b) => (
                  <div key={b.month} className="forecast-band-row">
                    <span className="text-xs tabular-nums text-[var(--muted)]">M{b.month}</span>
                    <div className="forecast-band-track">
                      <div
                        className="forecast-band-range"
                        style={{
                          left: toPct(b.p10),
                          width: `calc(${toPct(b.p90)} - ${toPct(b.p10)})`,
                        }}
                      />
                      <div className="forecast-band-median" style={{ left: toPct(b.p50) }} />
                    </div>
                    <span className="text-right text-[10px] tabular-nums text-[var(--muted)]">
                      {formatCurrency(b.p50)}
                    </span>
                  </div>
                ))}
              </div>

              {result.disclaimer && (
                <p className="text-[10px] leading-relaxed text-[var(--muted)]">{result.disclaimer}</p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
