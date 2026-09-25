"use client";

import { FlaskConical, Loader2, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState, type CSSProperties } from "react";

import { PageHeader } from "@/components/ui/PageHeader";
import { useAuthReady } from "@/hooks/useAuthReady";
import { api } from "@/lib/api";
import type { EvalRunSummary } from "@/lib/types";

function pct(v: number | undefined | null): string {
  if (v == null || Number.isNaN(v)) return "—";
  return `${(v * 100).toFixed(1)}%`;
}

function formatTs(ts: string): string {
  try {
    return new Date(ts).toLocaleString("en-CA", {
      dateStyle: "medium",
      timeStyle: "short",
    });
  } catch {
    return ts;
  }
}

export default function EvalsPage() {
  const authReady = useAuthReady();
  const [runs, setRuns] = useState<EvalRunSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getEvalRuns();
      setRuns(Array.isArray(data) ? data : []);
    } catch (e) {
      setRuns([]);
      setError(e instanceof Error ? e.message : "Failed to load eval runs");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!authReady) return;
    void load();
  }, [authReady, load]);

  return (
    <div className="page-container gap-6">
      <PageHeader
        eyebrow="Quality"
        title="Eval"
        titleAccent="Runs"
        subtitle="Harness history — answer accuracy, tool selection, hallucination rate, and retrieval."
        actions={
          <button
            type="button"
            onClick={() => void load()}
            disabled={loading}
            className="btn-ghost inline-flex items-center gap-2 px-3 py-2 text-sm"
          >
            {loading ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
            Refresh
          </button>
        }
      />

      {error && (
        <p className="rounded-xl border border-amber-500/25 bg-amber-500/5 px-4 py-3 text-sm text-[var(--foreground)]">
          {error}
          <span className="mt-1 block text-xs text-[var(--muted)]">
            The /evals API may be unavailable until the harness persists runs to the database.
          </span>
        </p>
      )}

      {loading ? (
        <div className="table-surface">
          <div className="space-y-0">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="shimmer mx-4 my-3 h-8 rounded" />
            ))}
          </div>
        </div>
      ) : runs.length === 0 ? (
        <div
          className="panel flex flex-col items-center gap-3 rounded-2xl py-14 text-center stagger-item"
          style={{ "--stagger": 1 } as CSSProperties}
        >
          <FlaskConical size={28} className="text-[var(--muted)]" />
          <p className="text-sm font-medium text-[var(--foreground)]">No eval runs yet</p>
          <p className="max-w-md text-xs text-[var(--muted)]">
            Run <code className="rounded bg-[var(--surface)] px-1.5 py-0.5 font-mono text-[10px]">
              uv run python -m evals.run --dry-run
            </code>{" "}
            on the API host to populate history.
          </p>
        </div>
      ) : (
        <div className="table-surface overflow-x-auto stagger-item" style={{ "--stagger": 1 } as CSSProperties}>
          <table className="w-full min-w-[720px]">
            <thead>
              <tr>
                <th>When</th>
                <th>Model</th>
                <th>Subset</th>
                <th>Questions</th>
                <th>Answer acc.</th>
                <th>Tool exact</th>
                <th>Halluc. $</th>
                <th>Refusal</th>
                <th>Recall@5</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run, i) => (
                <tr key={run.id ?? `${run.timestamp}-${i}`}>
                  <td className="whitespace-nowrap text-xs text-[var(--muted)]">
                    {formatTs(run.timestamp)}
                  </td>
                  <td className="font-medium">{run.model}</td>
                  <td>
                    <span className="rounded-md bg-[var(--accent-soft)] px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-[var(--accent)]">
                      {run.subset}
                      {run.dry_run ? " · dry" : ""}
                    </span>
                  </td>
                  <td className="tabular-nums">{run.n_questions}</td>
                  <td className="tabular-nums">{pct(run.answer_numeric_acc)}</td>
                  <td className="tabular-nums">{pct(run.tool_exact_acc)}</td>
                  <td className="tabular-nums">{pct(run.hallucinated_number_rate)}</td>
                  <td className="tabular-nums">{pct(run.refusal_acc)}</td>
                  <td className="tabular-nums">{pct(run.retrieval?.["recall@5"])}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
