"use client";

import { Code2, Database, Receipt, Wrench, X } from "lucide-react";
import { useEffect } from "react";

import type { EvidenceItem, Transaction } from "@/lib/types";
import { formatCurrency, formatDateShort } from "@/lib/utils";

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

function pickSql(result: Record<string, unknown> | null): string | null {
  if (!result) return null;
  for (const key of ["sql", "query", "snippet", "explanation"]) {
    const v = result[key];
    if (typeof v === "string" && v.trim()) return v;
  }
  return null;
}

function pickTransactions(result: Record<string, unknown> | null): Partial<Transaction>[] {
  if (!result) return [];
  const candidates = [result.transactions, result.items, result.results, result.rows];
  for (const c of candidates) {
    if (Array.isArray(c) && c.length > 0) {
      return c.filter((row) => row && typeof row === "object") as Partial<Transaction>[];
    }
  }
  return [];
}

export function EvidenceDrawer({
  open,
  evidenceId,
  evidence,
  onClose,
}: {
  open: boolean;
  evidenceId: string | null;
  evidence: EvidenceItem | null;
  onClose: () => void;
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  const result = asRecord(evidence?.result ?? null);
  const sql = pickSql(result);
  const txs = pickTransactions(result);
  const params = evidence?.params ?? {};
  const hasParams = Object.keys(params).length > 0;

  return (
    <>
      <button
        type="button"
        className="evidence-drawer-backdrop"
        aria-label="Close evidence drawer"
        onClick={onClose}
      />
      <aside
        className="evidence-drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby="evidence-drawer-title"
      >
        <div className="flex items-start justify-between gap-3 border-b border-[var(--border)] px-5 py-4">
          <div className="min-w-0">
            <p className="eyebrow">Evidence</p>
            <h2 id="evidence-drawer-title" className="mt-1 text-base font-semibold text-[var(--foreground)]">
              {evidenceId ?? "Unknown"}
            </h2>
            {evidence?.tool && (
              <p className="mt-1 flex items-center gap-1.5 text-xs text-[var(--muted)]">
                <Wrench size={12} className="text-[var(--accent)]" />
                {evidence.tool}
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="icon-btn"
            aria-label="Close"
          >
            <X size={16} />
          </button>
        </div>

        <div className="flex flex-1 flex-col gap-5 overflow-y-auto px-5 py-4">
          {!evidence ? (
            <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] px-4 py-6 text-center">
              <Database size={22} className="mx-auto text-[var(--muted)]" />
              <p className="mt-3 text-sm text-[var(--muted)]">
                No evidence payload for{" "}
                <span className="font-mono text-[var(--foreground)]">{evidenceId}</span>.
                It may not have been returned with this reply yet.
              </p>
            </div>
          ) : (
            <>
              {hasParams && (
                <section>
                  <h3 className="section-title mb-2">Parameters</h3>
                  <pre className="evidence-code">
                    {JSON.stringify(params, null, 2)}
                  </pre>
                </section>
              )}

              {sql && (
                <section>
                  <h3 className="mb-2 flex items-center gap-1.5 section-title">
                    <Code2 size={13} className="text-[var(--accent)]" />
                    SQL / snippet
                  </h3>
                  <pre className="evidence-code">{sql}</pre>
                </section>
              )}

              {txs.length > 0 && (
                <section>
                  <h3 className="mb-2 flex items-center gap-1.5 section-title">
                    <Receipt size={13} className="text-[var(--accent)]" />
                    Transactions
                  </h3>
                  <ul className="flex flex-col divide-y divide-[var(--border)] overflow-hidden rounded-xl border border-[var(--border)]">
                    {txs.slice(0, 25).map((tx, i) => (
                      <li
                        key={tx.id ?? `${i}`}
                        className="flex items-center gap-3 bg-[var(--surface)] px-3 py-2.5"
                      >
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm text-[var(--foreground)]">
                            {tx.description ?? tx.merchant ?? "Transaction"}
                          </p>
                          <p className="text-xs text-[var(--muted)]">
                            {[tx.category, tx.transaction_date ? formatDateShort(tx.transaction_date) : null]
                              .filter(Boolean)
                              .join(" · ") || "—"}
                          </p>
                        </div>
                        {tx.amount != null && (
                          <span
                            className={[
                              "shrink-0 text-sm font-medium tabular-nums",
                              tx.amount < 0 ? "text-rose-400" : "text-emerald-400",
                            ].join(" ")}
                          >
                            {tx.amount < 0 ? "-" : "+"}
                            {formatCurrency(tx.amount)}
                          </span>
                        )}
                      </li>
                    ))}
                  </ul>
                  {txs.length > 25 && (
                    <p className="mt-2 text-xs text-[var(--muted)]">
                      Showing 25 of {txs.length} rows
                    </p>
                  )}
                </section>
              )}

              {result && !sql && txs.length === 0 && (
                <section>
                  <h3 className="section-title mb-2">Tool result</h3>
                  <pre className="evidence-code">
                    {JSON.stringify(result, null, 2)}
                  </pre>
                </section>
              )}

              {result && (sql || txs.length > 0) && (
                <details className="rounded-xl border border-[var(--border)] bg-[var(--surface)]">
                  <summary className="cursor-pointer px-3 py-2 text-xs font-medium text-[var(--muted)]">
                    Raw result JSON
                  </summary>
                  <pre className="evidence-code border-0 rounded-none border-t border-[var(--border)]">
                    {JSON.stringify(result, null, 2)}
                  </pre>
                </details>
              )}
            </>
          )}
        </div>
      </aside>
    </>
  );
}
