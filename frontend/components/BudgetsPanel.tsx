"use client";

import { Plus, Trash2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { useToast } from "@/contexts/ToastContext";
import { useAuthReady } from "@/hooks/useAuthReady";
import { api } from "@/lib/api";
import type { Budget } from "@/lib/types";
import { formatCurrency } from "@/lib/utils";

const CATEGORIES = [
  "Dining", "Groceries", "Transport", "Housing", "Shopping",
  "Subscriptions", "Healthcare", "Entertainment", "Utilities",
];

export function BudgetsPanel({ stagger = 5 }: { stagger?: number }) {
  const { toast } = useToast();
  const authReady = useAuthReady();
  const [budgets, setBudgets] = useState<Budget[]>([]);
  const [loading, setLoading] = useState(true);
  const [category, setCategory] = useState(CATEGORIES[0]);
  const [limit, setLimit] = useState("");
  const [saving, setSaving] = useState(false);

  const load = useCallback(() => {
    return api.getBudgets().then(setBudgets).catch(() => setBudgets([]));
  }, []);

  useEffect(() => {
    if (!authReady) return;
    void load().finally(() => setLoading(false));
  }, [authReady, load]);

  const handleAdd = async () => {
    const amount = parseFloat(limit);
    if (!amount || amount <= 0) return;
    setSaving(true);
    try {
      await api.createBudget({ category, monthly_limit: amount });
      setLimit("");
      await load();
      toast("Budget added");
    } catch {
      toast("Could not add budget", "error");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await api.deleteBudget(id);
      setBudgets((prev) => prev.filter((b) => b.id !== id));
      toast("Budget removed");
    } catch {
      toast("Could not remove budget", "error");
    }
  };

  if (loading) {
    return <div className="panel h-40 shimmer rounded-2xl" />;
  }

  return (
    <section
      className="panel stagger-item rounded-2xl p-6"
      style={{ "--stagger": stagger } as React.CSSProperties}
    >
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <p className="eyebrow">Budgets</p>
          <h2 className="section-title mt-0.5">Monthly limits</h2>
        </div>
      </div>

      {budgets.length === 0 ? (
        <p className="mb-4 text-sm text-[var(--muted)]">
          Set category limits to get spend alerts when you go over budget.
        </p>
      ) : (
        <ul className="mb-5 flex flex-col gap-3">
          {budgets.map((b) => (
            <li key={b.id} className="rounded-xl border border-[var(--border)] bg-[var(--surface)] px-4 py-3">
              <div className="mb-2 flex items-center justify-between gap-2">
                <span className="text-sm font-medium text-[var(--foreground)]">{b.category}</span>
                <div className="flex items-center gap-2">
                  <span className="text-xs tabular-nums text-[var(--muted)]">
                    {formatCurrency(b.spent_this_month)} / {formatCurrency(b.monthly_limit)}
                  </span>
                  <button
                    type="button"
                    onClick={() => void handleDelete(b.id)}
                    className="rounded-lg p-1 text-[var(--muted)] hover:bg-rose-500/10 hover:text-rose-400"
                    aria-label="Remove budget"
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-[var(--surface-elevated)]">
                <div
                  className={[
                    "h-full rounded-full transition-all",
                    b.percent_used >= 100 ? "bg-rose-500" : "bg-gradient-to-r from-teal-500 to-blue-600",
                  ].join(" ")}
                  style={{ width: `${Math.min(b.percent_used, 100)}%` }}
                />
              </div>
            </li>
          ))}
        </ul>
      )}

      <div className="form-inline">
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="select-field min-w-[9rem] flex-1 sm:flex-none"
        >
          {CATEGORIES.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
        <input
          type="number"
          min="1"
          step="1"
          placeholder="Monthly limit"
          value={limit}
          onChange={(e) => setLimit(e.target.value)}
          className="input-field input-field--sm w-full min-w-[8rem] sm:w-36"
        />
        <button
          type="button"
          onClick={() => void handleAdd()}
          disabled={saving || !limit}
          className="btn-primary inline-flex items-center gap-1.5 disabled:opacity-40"
        >
          <Plus size={13} />
          Add
        </button>
      </div>
    </section>
  );
}
