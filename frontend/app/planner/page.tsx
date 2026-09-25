"use client";

import { Calculator, GraduationCap, Loader2 } from "lucide-react";
import { useState, type CSSProperties, type FormEvent } from "react";

import { PageHeader } from "@/components/ui/PageHeader";
import { api } from "@/lib/api";
import { formatCurrency } from "@/lib/utils";

type Tab = "registered" | "osap";

function num(v: FormDataEntryValue | null, fallback = 0): number {
  const n = Number(v);
  return Number.isFinite(n) ? n : fallback;
}

export default function PlannerPage() {
  const [tab, setTab] = useState<Tab>("registered");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [registered, setRegistered] = useState<Record<string, unknown> | null>(null);
  const [osap, setOsap] = useState<Record<string, unknown> | null>(null);

  const onRegistered = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    const fd = new FormData(e.currentTarget);
    try {
      const result = await api.runRegisteredOptimizer({
        income: num(fd.get("income")),
        age: Math.round(num(fd.get("age"), 22)),
        first_time_buyer: fd.get("first_time_buyer") === "on",
        horizon: Math.round(num(fd.get("horizon"), 5)),
        annual_contribution: num(fd.get("annual_contribution")),
        tax_year: Math.round(num(fd.get("tax_year"), 2026)),
        existing_room: {
          tfsa: num(fd.get("room_tfsa")),
          rrsp: num(fd.get("room_rrsp")),
          fhsa: num(fd.get("room_fhsa")),
        },
      });
      setRegistered(result);
    } catch (err) {
      setRegistered(null);
      setError(err instanceof Error ? err.message : "Optimizer failed");
    } finally {
      setLoading(false);
    }
  };

  const onOsap = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    const fd = new FormData(e.currentTarget);
    try {
      const result = await api.runOsapPlan({
        principal: num(fd.get("principal")),
        annual_rate: fd.get("annual_rate") === "" ? null : num(fd.get("annual_rate")),
        standard_years: fd.get("standard_years") === "" ? null : num(fd.get("standard_years")),
        accelerated_years:
          fd.get("accelerated_years") === "" ? null : num(fd.get("accelerated_years")),
        extra_monthly: num(fd.get("extra_monthly")),
        tax_year: Math.round(num(fd.get("tax_year"), 2026)),
      });
      setOsap(result);
    } catch (err) {
      setOsap(null);
      setError(err instanceof Error ? err.message : "OSAP plan failed");
    } finally {
      setLoading(false);
    }
  };

  const years = Array.isArray(registered?.years)
    ? (registered.years as Array<Record<string, unknown>>)
    : [];
  const totals = (registered?.totals as Record<string, number> | undefined) ?? undefined;
  const ending = (registered?.ending_balances as Record<string, number> | undefined) ?? undefined;

  const std = (osap?.standard as Record<string, number> | undefined) ?? undefined;
  const accel = (osap?.accelerated as Record<string, number> | undefined) ?? undefined;
  const extra = (osap?.with_extra_payments as Record<string, number> | undefined) ?? undefined;

  return (
    <div className="page-container gap-6">
      <PageHeader
        eyebrow="Canadian planning"
        title="Registered &"
        titleAccent="OSAP"
        subtitle="Deterministic TFSA / RRSP / FHSA allocation and OSAP repayment scenarios — not tax advice."
      />

      <div className="flex flex-wrap gap-2">
        {(
          [
            { id: "registered" as const, label: "Registered optimizer", icon: Calculator },
            { id: "osap" as const, label: "OSAP repayment", icon: GraduationCap },
          ] as const
        ).map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            onClick={() => setTab(id)}
            className={[
              "inline-flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-medium",
              tab === id ? "btn-primary" : "btn-ghost",
            ].join(" ")}
          >
            <Icon size={14} />
            {label}
          </button>
        ))}
      </div>

      {error && (
        <p className="rounded-xl border border-rose-500/25 bg-rose-500/5 px-4 py-3 text-sm text-rose-400">
          {error}
        </p>
      )}

      {tab === "registered" && (
        <div className="grid gap-6 lg:grid-cols-2">
          <form
            onSubmit={(e) => void onRegistered(e)}
            className="panel flex flex-col gap-4 rounded-2xl p-5 stagger-item"
            style={{ "--stagger": 1 } as CSSProperties}
          >
            <h2 className="section-title">Inputs</h2>
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="text-xs text-[var(--muted)]">
                Income (CAD)
                <input name="income" type="number" min={0} step={100} defaultValue={45000} required className="input-field mt-1" />
              </label>
              <label className="text-xs text-[var(--muted)]">
                Age
                <input name="age" type="number" min={0} max={120} defaultValue={22} required className="input-field mt-1" />
              </label>
              <label className="text-xs text-[var(--muted)]">
                Annual contribution
                <input name="annual_contribution" type="number" min={0} step={100} defaultValue={8000} className="input-field mt-1" />
              </label>
              <label className="text-xs text-[var(--muted)]">
                Horizon (years)
                <input name="horizon" type="number" min={1} max={50} defaultValue={5} className="input-field mt-1" />
              </label>
              <label className="text-xs text-[var(--muted)]">
                Tax year
                <input name="tax_year" type="number" defaultValue={2026} className="input-field mt-1" />
              </label>
              <label className="flex items-center gap-2 pt-5 text-sm text-[var(--foreground)]">
                <input name="first_time_buyer" type="checkbox" defaultChecked className="accent-[var(--accent)]" />
                First-time home buyer
              </label>
              <label className="text-xs text-[var(--muted)]">
                Existing TFSA room
                <input name="room_tfsa" type="number" min={0} defaultValue={0} className="input-field mt-1" />
              </label>
              <label className="text-xs text-[var(--muted)]">
                Existing RRSP room
                <input name="room_rrsp" type="number" min={0} defaultValue={0} className="input-field mt-1" />
              </label>
              <label className="text-xs text-[var(--muted)]">
                Existing FHSA room
                <input name="room_fhsa" type="number" min={0} defaultValue={0} className="input-field mt-1" />
              </label>
            </div>
            <button type="submit" disabled={loading} className="btn-primary mt-2 inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm">
              {loading && tab === "registered" ? <Loader2 size={14} className="animate-spin" /> : null}
              Run optimizer
            </button>
          </form>

          <div
            className="panel rounded-2xl p-5 stagger-item"
            style={{ "--stagger": 2 } as CSSProperties}
          >
            <h2 className="section-title">Results</h2>
            {!registered && !loading && (
              <p className="mt-6 text-center text-sm text-[var(--muted)]">
                Enter income and contribution to see FHSA / TFSA / RRSP allocation.
              </p>
            )}
            {loading && tab === "registered" && (
              <div className="mt-4 space-y-3">
                <div className="shimmer h-8 rounded-lg" />
                <div className="shimmer h-32 rounded-xl" />
              </div>
            )}
            {registered && !loading && (
              <div className="mt-4 flex flex-col gap-4">
                {Array.isArray(registered.allocation_priority) && (
                  <p className="text-xs text-[var(--muted)]">
                    Priority:{" "}
                    <span className="font-medium text-[var(--foreground)]">
                      {(registered.allocation_priority as string[]).join(" → ").toUpperCase()}
                    </span>
                  </p>
                )}
                {ending && (
                  <div className="grid grid-cols-3 gap-2">
                    {Object.entries(ending).map(([k, v]) => (
                      <div key={k} className="rounded-xl border border-[var(--border)] bg-[var(--surface)] px-3 py-2">
                        <p className="text-[10px] uppercase tracking-wider text-[var(--muted)]">{k}</p>
                        <p className="mt-0.5 text-sm font-semibold tabular-nums">{formatCurrency(v)}</p>
                      </div>
                    ))}
                  </div>
                )}
                {totals && (
                  <p className="text-xs text-[var(--muted)]">
                    Total contributed:{" "}
                    {Object.entries(totals)
                      .map(([k, v]) => `${k.toUpperCase()} ${formatCurrency(v)}`)
                      .join(" · ")}
                  </p>
                )}
                {years.length > 0 && (
                  <div className="table-surface overflow-x-auto">
                    <table className="w-full min-w-[320px]">
                      <thead>
                        <tr>
                          <th>Year</th>
                          <th>FHSA</th>
                          <th>TFSA</th>
                          <th>RRSP</th>
                        </tr>
                      </thead>
                      <tbody>
                        {years.slice(0, 10).map((y, i) => (
                          <tr key={i}>
                            <td>{String(y.year ?? i + 1)}</td>
                            <td className="tabular-nums">{formatCurrency(Number(y.fhsa ?? 0))}</td>
                            <td className="tabular-nums">{formatCurrency(Number(y.tfsa ?? 0))}</td>
                            <td className="tabular-nums">{formatCurrency(Number(y.rrsp ?? 0))}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
                {typeof registered.disclaimer === "string" && (
                  <p className="text-[10px] leading-relaxed text-[var(--muted)]">{registered.disclaimer}</p>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {tab === "osap" && (
        <div className="grid gap-6 lg:grid-cols-2">
          <form
            onSubmit={(e) => void onOsap(e)}
            className="panel flex flex-col gap-4 rounded-2xl p-5 stagger-item"
            style={{ "--stagger": 1 } as CSSProperties}
          >
            <h2 className="section-title">Loan inputs</h2>
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="text-xs text-[var(--muted)]">
                Principal
                <input name="principal" type="number" min={0} step={100} defaultValue={12000} required className="input-field mt-1" />
              </label>
              <label className="text-xs text-[var(--muted)]">
                Annual rate (optional)
                <input name="annual_rate" type="number" min={0} max={1} step={0.001} placeholder="e.g. 0.065" className="input-field mt-1" />
              </label>
              <label className="text-xs text-[var(--muted)]">
                Standard years
                <input name="standard_years" type="number" min={0} step={0.5} placeholder="default from rules" className="input-field mt-1" />
              </label>
              <label className="text-xs text-[var(--muted)]">
                Accelerated years
                <input name="accelerated_years" type="number" min={0} step={0.5} className="input-field mt-1" />
              </label>
              <label className="text-xs text-[var(--muted)]">
                Extra monthly
                <input name="extra_monthly" type="number" min={0} step={25} defaultValue={0} className="input-field mt-1" />
              </label>
              <label className="text-xs text-[var(--muted)]">
                Tax year
                <input name="tax_year" type="number" defaultValue={2026} className="input-field mt-1" />
              </label>
            </div>
            <button type="submit" disabled={loading} className="btn-primary mt-2 inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm">
              {loading && tab === "osap" ? <Loader2 size={14} className="animate-spin" /> : null}
              Plan repayment
            </button>
          </form>

          <div
            className="panel rounded-2xl p-5 stagger-item"
            style={{ "--stagger": 2 } as CSSProperties}
          >
            <h2 className="section-title">Scenarios</h2>
            {!osap && !loading && (
              <p className="mt-6 text-center text-sm text-[var(--muted)]">
                Enter principal to compare standard, accelerated, and extra-payment paths.
              </p>
            )}
            {loading && tab === "osap" && (
              <div className="mt-4 space-y-3">
                <div className="shimmer h-20 rounded-xl" />
                <div className="shimmer h-20 rounded-xl" />
              </div>
            )}
            {osap && !loading && (
              <div className="mt-4 grid gap-3">
                {[
                  { label: "Standard", data: std },
                  { label: "Accelerated", data: accel },
                  { label: "With extra", data: extra },
                ].map(({ label, data }) =>
                  data ? (
                    <div key={label} className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4">
                      <p className="text-xs font-semibold uppercase tracking-wider text-[var(--muted)]">
                        {label}
                      </p>
                      <p className="mt-1 text-lg font-semibold tabular-nums text-[var(--foreground)]">
                        {formatCurrency(Number(data.monthly_payment ?? 0))}
                        <span className="text-xs font-normal text-[var(--muted)]"> / mo</span>
                      </p>
                      <p className="mt-1 text-xs text-[var(--muted)]">
                        {data.months ?? "—"} months · interest{" "}
                        {formatCurrency(Number(data.total_interest ?? 0))}
                        {data.interest_saved_vs_standard != null && (
                          <> · saves {formatCurrency(Number(data.interest_saved_vs_standard))}</>
                        )}
                      </p>
                    </div>
                  ) : null,
                )}
                {typeof osap.disclaimer === "string" && (
                  <p className="text-[10px] leading-relaxed text-[var(--muted)]">{osap.disclaimer}</p>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
