"use client";

import { AlertTriangle, Database, RefreshCw } from "lucide-react";

/** Shown only when data failed to load — no infra/debug messaging. */
export function DataStatusBanner({
  error,
  onRetry,
  loading,
}: {
  error: string | null;
  onRetry?: () => void;
  loading?: boolean;
}) {
  if (!error) return null;

  const isDb = Boolean(
    error.toLowerCase().includes("database") ||
      error.includes("500") ||
      error.includes("column"),
  );

  const userMessage = isDb
    ? "We couldn't load your data right now. Please try again in a moment."
    : error.replace(/^API \d+:\s*/i, "").slice(0, 200);

  return (
    <div
      className="stagger-item panel-glow flex flex-col gap-3 rounded-2xl border border-rose-500/30 bg-rose-500/5 px-5 py-4 sm:flex-row sm:items-center sm:justify-between"
      style={{ "--stagger": 1 } as React.CSSProperties}
    >
      <div className="flex gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-rose-500/15 text-rose-400">
          {isDb ? <Database size={18} /> : <AlertTriangle size={18} />}
        </div>
        <div className="min-w-0">
          <p className="text-sm font-semibold text-[var(--foreground)]">Unable to load your data</p>
          <p className="mt-1 text-xs leading-relaxed text-[var(--muted)]">{userMessage}</p>
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
