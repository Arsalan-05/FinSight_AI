"use client";

import { AlertTriangle, Database, RefreshCw, Wifi } from "lucide-react";

export function DataStatusBanner({
  error,
  usingFallback,
  dbHost,
  onRetry,
  loading,
}: {
  error: string | null;
  usingFallback?: boolean;
  dbHost?: string | null;
  onRetry?: () => void;
  loading?: boolean;
}) {
  if (!error && !usingFallback) return null;

  const isDb = Boolean(error?.toLowerCase().includes("database") || error?.includes("500") || error?.includes("column"));

  return (
    <div
      className={[
        "stagger-item panel-glow flex flex-col gap-3 rounded-2xl border px-5 py-4 sm:flex-row sm:items-center sm:justify-between",
        error ? "border-rose-500/30 bg-rose-500/5" : "border-amber-500/25 bg-amber-500/5",
      ].join(" ")}
      style={{ "--stagger": 1 } as React.CSSProperties}
    >
      <div className="flex gap-3">
        <div
          className={[
            "flex h-10 w-10 shrink-0 items-center justify-center rounded-xl",
            error ? "bg-rose-500/15 text-rose-400" : "bg-amber-500/15 text-amber-400",
          ].join(" ")}
        >
          {isDb ? <Database size={18} /> : error ? <AlertTriangle size={18} /> : <Wifi size={18} />}
        </div>
        <div className="min-w-0">
          <p className="text-sm font-semibold text-zinc-100">
            {error ? "Unable to load your data" : "Using local database"}
          </p>
          <p className="mt-1 text-xs leading-relaxed text-zinc-500">
            {error ??
              `Connected to ${dbHost ?? "local Postgres"}. Supabase cloud data is not on this instance — demo data loads here automatically.`}
          </p>
          {error?.includes("column") && (
            <p className="mt-2 font-mono text-[11px] text-amber-400/90">
              Fix: cd backend && uv run alembic upgrade head
            </p>
          )}
        </div>
      </div>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          disabled={loading}
          className="btn-primary inline-flex shrink-0 items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-medium disabled:opacity-50"
        >
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          Retry
        </button>
      )}
    </div>
  );
}
