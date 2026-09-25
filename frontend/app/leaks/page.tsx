"use client";

import {
  AlertTriangle,
  CheckCircle2,
  Droplets,
  Loader2,
  RefreshCw,
} from "lucide-react";
import { useCallback, useEffect, useState, type CSSProperties } from "react";

import { PageHeader } from "@/components/ui/PageHeader";
import { useAuthReady } from "@/hooks/useAuthReady";
import { api } from "@/lib/api";
import type { LeakFinding, LeakSummary } from "@/lib/types";
import { formatCurrency } from "@/lib/utils";

function statusLabel(status: string): string {
  if (status === "resolved") return "Resolved";
  if (status === "dismissed") return "Dismissed";
  return "Open";
}

function typeLabel(type: string): string {
  return type.replace(/_/g, " ");
}

export default function LeaksPage() {
  const authReady = useAuthReady();
  const [findings, setFindings] = useState<LeakFinding[]>([]);
  const [summary, setSummary] = useState<LeakSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = useCallback(async (rescan = false) => {
    setLoading(true);
    setError(null);
    try {
      const [list, sum] = await Promise.all([
        api.getLeaks(rescan),
        api.getLeaksSummary(),
      ]);
      setFindings(list);
      setSummary(sum);
    } catch (e) {
      setFindings([]);
      setSummary(null);
      setError(e instanceof Error ? e.message : "Failed to load leaks");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!authReady) return;
    void load(false);
  }, [authReady, load]);

  const updateStatus = async (id: string, status: string) => {
    setBusyId(id);
    try {
      const updated = await api.updateLeak(id, { status });
      setFindings((prev) => prev.map((f) => (f.id === id ? updated : f)));
      const sum = await api.getLeaksSummary();
      setSummary(sum);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Update failed");
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="page-container gap-6">
      <PageHeader
        eyebrow="Recovery"
        title="Money"
        titleAccent="Leaks"
        subtitle="Fees, duplicates, FX markup, and forgotten subscriptions detected from your transactions."
        actions={
          <button
            type="button"
            onClick={() => void load(true)}
            disabled={loading}
            className="btn-ghost inline-flex items-center gap-2 px-3 py-2 text-sm"
          >
            {loading ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
            Rescan
          </button>
        }
      />

      <div
        className="panel kpi-card kpi-accent-emerald panel-interactive rounded-2xl stagger-item"
        style={{ "--stagger": 1 } as CSSProperties}
      >
        <div className="flex items-center gap-2 text-[var(--muted)]">
          <span className="kpi-icon">
            <Droplets size={15} />
          </span>
          <span className="text-xs font-medium uppercase tracking-wider">Money Recovered</span>
        </div>
        {loading ? (
          <div className="shimmer mt-2 h-10 w-40 rounded-lg" />
        ) : (
          <>
            <p className="text-3xl font-semibold tabular-nums text-[var(--foreground)]">
              {formatCurrency(summary?.total_resolved_cad ?? 0)}
            </p>
            <p className="text-xs text-[var(--muted)]">
              {formatCurrency(summary?.total_found_cad ?? 0)} found ·{" "}
              {summary?.open_count ?? 0} open (
              {formatCurrency(summary?.open_amount_cad ?? 0)})
            </p>
          </>
        )}
      </div>

      {error && (
        <div className="flex items-start gap-2 rounded-xl border border-rose-500/25 bg-rose-500/5 px-4 py-3 text-sm text-rose-400">
          <AlertTriangle size={16} className="mt-0.5 shrink-0" />
          <p>{error}</p>
        </div>
      )}

      {loading ? (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="shimmer h-24 rounded-2xl" />
          ))}
        </div>
      ) : findings.length === 0 ? (
        <div className="panel flex flex-col items-center gap-3 rounded-2xl py-14 text-center">
          <CheckCircle2 size={28} className="text-[var(--accent)]" />
          <p className="text-sm font-medium text-[var(--foreground)]">No leak findings yet</p>
          <p className="max-w-sm text-xs text-[var(--muted)]">
            Import transactions and rescan — FinSight looks for bank fees, duplicates, FX markup,
            and forgotten subscriptions.
          </p>
        </div>
      ) : (
        <ul className="flex flex-col gap-3">
          {findings.map((f, i) => (
            <li
              key={f.id}
              className="panel rounded-2xl p-4 sm:p-5 stagger-item"
              style={{ "--stagger": i + 2 } as CSSProperties}
            >
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="rounded-md bg-[var(--accent-soft)] px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-[var(--accent)]">
                      {typeLabel(f.type)}
                    </span>
                    <span
                      className={[
                        "rounded-md px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider",
                        f.status === "resolved"
                          ? "bg-emerald-500/10 text-emerald-400"
                          : f.status === "dismissed"
                            ? "bg-[var(--surface)] text-[var(--muted)]"
                            : "bg-amber-500/10 text-amber-400",
                      ].join(" ")}
                    >
                      {statusLabel(f.status)}
                    </span>
                  </div>
                  <p className="mt-2 text-sm font-medium text-[var(--foreground)]">
                    {f.title || typeLabel(f.type)}
                  </p>
                  {f.message && (
                    <p className="mt-1 text-xs leading-relaxed text-[var(--muted)]">{f.message}</p>
                  )}
                </div>
                <div className="flex shrink-0 flex-col items-start gap-2 sm:items-end">
                  <p className="text-lg font-semibold tabular-nums text-[var(--foreground)]">
                    {formatCurrency(f.amount_cad)}
                  </p>
                  {f.status === "open" && (
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        disabled={busyId === f.id}
                        onClick={() => void updateStatus(f.id, "resolved")}
                        className="btn-primary rounded-lg px-3 py-1.5 text-xs disabled:opacity-50"
                      >
                        Mark recovered
                      </button>
                      <button
                        type="button"
                        disabled={busyId === f.id}
                        onClick={() => void updateStatus(f.id, "dismissed")}
                        className="btn-ghost rounded-lg px-3 py-1.5 text-xs disabled:opacity-50"
                      >
                        Dismiss
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
