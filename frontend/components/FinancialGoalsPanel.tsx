"use client";

import { MessageSquare, Plus, Target, Trash2 } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState, type CSSProperties } from "react";

import { useToast } from "@/contexts/ToastContext";
import { useAuthReady } from "@/hooks/useAuthReady";
import { api } from "@/lib/api";
import { chatUrl } from "@/lib/chat-url";
import type { FinancialGoal } from "@/lib/types";
import { isSupabaseConfigured } from "@/lib/supabase/client";

function goalProgress(goal: FinancialGoal): number | null {
  if (goal.target_amount == null || goal.target_amount <= 0) return null;
  const current = goal.current_amount ?? 0;
  return Math.min(100, Math.round((current / goal.target_amount) * 100));
}

function isOverdue(deadline?: string | null): boolean {
  if (!deadline) return false;
  const d = new Date(deadline);
  return !Number.isNaN(d.getTime()) && d < new Date();
}

export function FinancialGoalsPanel({ stagger = 2 }: { stagger?: number }) {
  const { toast } = useToast();
  const authReady = useAuthReady();
  const [goals, setGoals] = useState<FinancialGoal[]>([]);
  const [loading, setLoading] = useState(true);
  const [goalTitle, setGoalTitle] = useState("");
  const [goalAmount, setGoalAmount] = useState("");
  const [expanded, setExpanded] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editCurrent, setEditCurrent] = useState("");

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

  const saveProgress = (goalId: string) => {
    const value = parseFloat(editCurrent);
    if (Number.isNaN(value)) return;
    void api
      .updateGoal(goalId, { current_amount: value })
      .then((updated) => {
        setGoals((prev) => prev.map((g) => (g.id === goalId ? updated : g)));
        setEditingId(null);
        toast("Progress updated");
      })
      .catch(() => toast("Could not update progress", "error"));
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
              Track progress — your agent references these in advice
            </p>
          </div>
        </div>
        <Link
          href={chatUrl("How am I tracking toward my savings goals and what should I change?")}
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
              {goals.map((g) => {
                const pct = goalProgress(g);
                const overdue = isOverdue(g.deadline);
                return (
                  <li
                    key={g.id}
                    className="rounded-xl border border-[var(--border)] bg-[var(--surface)] px-4 py-3"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium text-[var(--foreground)]">
                          {g.title}
                        </p>
                        {g.target_amount != null && (
                          <p className="mt-0.5 text-xs tabular-nums text-[var(--muted)]">
                            ${(g.current_amount ?? 0).toLocaleString()} of $
                            {g.target_amount.toLocaleString()}
                            {g.deadline && (
                              <span className={overdue ? " text-rose-400" : ""}>
                                {" "}
                                · due {g.deadline}
                              </span>
                            )}
                          </p>
                        )}
                        {pct != null && (
                          <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-[var(--surface-elevated)]">
                            <div
                              className="h-full rounded-full bg-gradient-to-r from-teal-500 to-blue-600 transition-all"
                              style={{ width: `${pct}%` }}
                            />
                          </div>
                        )}
                        {editingId === g.id ? (
                          <div className="form-inline mt-2">
                            <input
                              type="number"
                              value={editCurrent}
                              onChange={(e) => setEditCurrent(e.target.value)}
                              placeholder="Current saved $"
                              className="input-field input-field--sm w-32"
                            />
                            <button
                              type="button"
                              onClick={() => saveProgress(g.id)}
                              className="btn-primary text-xs"
                            >
                              Save
                            </button>
                            <button
                              type="button"
                              onClick={() => setEditingId(null)}
                              className="btn-ghost text-xs"
                            >
                              Cancel
                            </button>
                          </div>
                        ) : (
                          <button
                            type="button"
                            onClick={() => {
                              setEditingId(g.id);
                              setEditCurrent(
                                g.current_amount != null ? String(g.current_amount) : "",
                              );
                            }}
                            className="link-accent mt-2 text-xs"
                          >
                            Update progress
                          </button>
                        )}
                      </div>
                      <div className="flex shrink-0 items-center gap-1">
                        <Link
                          href={chatUrl(`How am I tracking toward my goal: ${g.title}?`)}
                          className="rounded-lg p-2 text-[var(--muted)] hover:bg-[var(--accent-soft)] hover:text-[var(--accent)]"
                          aria-label={`Ask about ${g.title}`}
                        >
                          <MessageSquare size={14} />
                        </Link>
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
                      </div>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}

          {goals.length === 0 && !expanded && (
            <p className="mb-3 text-sm text-[var(--muted)]">
              Set a rent buffer, emergency fund, or tuition target — the agent uses these in advice.
            </p>
          )}

          {expanded ? (
            <div className="form-inline">
              <input
                value={goalTitle}
                onChange={(e) => setGoalTitle(e.target.value)}
                placeholder="Goal name"
                className="input-field input-field--sm min-w-[10rem] flex-1"
                autoFocus
              />
              <input
                value={goalAmount}
                onChange={(e) => setGoalAmount(e.target.value)}
                placeholder="Target $"
                type="number"
                className="input-field input-field--sm w-full min-w-[7rem] sm:w-32"
              />
              <button type="button" onClick={handleAdd} className="btn-primary">
                Save
              </button>
              <button
                type="button"
                onClick={() => setExpanded(false)}
                className="btn-ghost"
              >
                Cancel
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => setExpanded(true)}
              className="btn-ghost inline-flex items-center gap-2 px-4 py-2.5 text-sm"
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
