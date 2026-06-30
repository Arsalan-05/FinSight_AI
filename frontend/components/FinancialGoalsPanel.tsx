"use client";

import { MessageSquare, Plus, Target, Trash2 } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState, type CSSProperties } from "react";

import { useToast } from "@/contexts/ToastContext";
import { useAuthReady } from "@/hooks/useAuthReady";
import { api } from "@/lib/api";
import type { FinancialGoal } from "@/lib/types";
import { isSupabaseConfigured } from "@/lib/supabase/client";

export function FinancialGoalsPanel({ stagger = 2 }: { stagger?: number }) {
  const { toast } = useToast();
  const authReady = useAuthReady();
  const [goals, setGoals] = useState<FinancialGoal[]>([]);
  const [loading, setLoading] = useState(true);
  const [goalTitle, setGoalTitle] = useState("");
  const [goalAmount, setGoalAmount] = useState("");
  const [expanded, setExpanded] = useState(false);

  const refresh = useCallback(() => {
    if (!authReady || !isSupabaseConfigured()) {
      setLoading(false);
      return;
    }
    api
      .getGoals()
      .then(setGoals)
      .catch(() => setGoals([]))
      .finally(() => setLoading(false));
  }, [authReady]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  if (!isSupabaseConfigured()) return null;

  const handleAdd = () => {
    if (!goalTitle.trim()) return;
    void api
      .createGoal({
        title: goalTitle.trim(),
        target_amount: goalAmount ? parseFloat(goalAmount) : undefined,
      })
      .then((g) => {
        setGoals((prev) => [...prev, g]);
        setGoalTitle("");
        setGoalAmount("");
        setExpanded(false);
        toast("Goal saved — your agent will reference it");
      })
      .catch(() => toast("Sign in to save goals", "error"));
  };

  return (
    <section
      className="panel rounded-2xl p-6 stagger-item"
      style={{ "--stagger": stagger } as CSSProperties}
    >
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[var(--accent-soft)]">
            <Target size={17} className="text-[var(--accent)]" />
          </div>
          <div>
            <h2 className="section-title">Savings goals</h2>
            <p className="mt-0.5 text-xs text-[var(--muted)]">
              Tracked on your overview — referenced by the finance agent
            </p>
          </div>
        </div>
        <Link
          href="/chat"
          className="btn-ghost inline-flex items-center gap-1.5 px-3 py-1.5 text-xs"
        >
          <MessageSquare size={13} />
          Ask agent
        </Link>
      </div>

      {loading ? (
        <div className="space-y-2">
          <div className="h-14 shimmer rounded-xl" />
          <div className="h-14 shimmer rounded-xl" />
        </div>
      ) : (
        <>
          {goals.length > 0 && (
            <ul className="mb-4 flex flex-col gap-2">
              {goals.map((g) => (
                <li
                  key={g.id}
                  className="flex items-center justify-between gap-3 rounded-xl border border-[var(--border)] bg-[var(--surface)] px-4 py-3"
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-[var(--foreground)]">
                      {g.title}
                    </p>
                    {g.target_amount != null && (
                      <p className="mt-0.5 text-xs tabular-nums text-[var(--muted)]">
                        Target ${g.target_amount.toLocaleString()}
                      </p>
                    )}
                  </div>
                  <button
                    type="button"
                    onClick={() =>
                      void api.deleteGoal(g.id).then(() => {
                        setGoals((prev) => prev.filter((x) => x.id !== g.id));
                      })
                    }
                    className="shrink-0 rounded-lg p-2 text-[var(--muted)] hover:bg-rose-500/10 hover:text-rose-400"
                    aria-label="Remove goal"
                  >
                    <Trash2 size={14} />
                  </button>
                </li>
              ))}
            </ul>
          )}

          {goals.length === 0 && !expanded && (
            <p className="mb-3 text-sm text-[var(--muted)]">
              Set a rent buffer, emergency fund, or tuition target — the agent uses these in advice.
            </p>
          )}

          {expanded ? (
            <div className="flex flex-col gap-2 sm:flex-row">
              <input
                value={goalTitle}
                onChange={(e) => setGoalTitle(e.target.value)}
                placeholder="Goal name"
                className="input-field flex-1"
                autoFocus
              />
              <input
                value={goalAmount}
                onChange={(e) => setGoalAmount(e.target.value)}
                placeholder="Target $"
                type="number"
                className="input-field w-full sm:w-28"
              />
              <button type="button" onClick={handleAdd} className="btn-primary px-4 py-2.5 text-sm">
                Save
              </button>
              <button
                type="button"
                onClick={() => setExpanded(false)}
                className="btn-ghost px-4 py-2.5 text-sm"
              >
                Cancel
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => setExpanded(true)}
              className="btn-ghost inline-flex items-center gap-2 px-4 py-2 text-sm"
            >
              <Plus size={14} />
              {goals.length === 0 ? "Add your first goal" : "Add another goal"}
            </button>
          )}
        </>
      )}
    </section>
  );
}
