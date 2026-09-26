"use client";

import { Calendar, ChevronRight, Database, Filter, Receipt, X } from "lucide-react";
import { useEffect } from "react";

import type { EvidenceItem, Transaction } from "@/lib/types";
import { formatCurrency, formatDate, formatDateShort } from "@/lib/utils";

type Row = Record<string, unknown>;

const SOURCE_LABELS: Record<string, string> = {
  aggregate_spending: "Spending totals from your transactions",
  search_transactions: "Matching transactions",
  get_financial_insights: "Your financial insights",
  get_user_financial_profile: "Your spending patterns",
  get_tfsa_status: "TFSA contribution room",
  get_cash_runway: "Cash runway estimate",
  calculate: "Calculation",
  search_web: "Web research",
  convert_currency: "Currency conversion",
  get_exchange_rates: "Exchange rates",
  get_market_quote: "Market quote",
  run_registered_optimizer: "TFSA / RRSP / FHSA plan",
  run_osap_plan: "OSAP repayment plan",
  run_cash_forecast: "Cash forecast",
};

const PERIOD_LABELS: Record<string, string> = {
  last_month: "Last month",
  this_month: "This month",
  last_30_days: "Last 30 days",
  all: "All time",
  nearest_month_with_data: "Most recent month with data",
};

const TYPE_LABELS: Record<string, string> = {
  debit: "Expenses only",
  credit: "Income only",
  all: "Income and expenses",
};

const GROUP_LABELS: Record<string, string> = {
  category: "By category",
  merchant: "By merchant",
  month: "By month",
};

function asRecord(value: unknown): Row | null {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Row) : null;
}

function asNumber(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim() && !Number.isNaN(Number(value))) return Number(value);
  return null;
}

function asString(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value : null;
}

function pickTransactions(result: Row | null): Partial<Transaction>[] {
  if (!result) return [];
  for (const c of [result.transactions, result.items, result.results, result.rows]) {
    if (Array.isArray(c) && c.length > 0) {
      return c
        .filter((row) => row && typeof row === "object")
        .map((row) => {
          const r = row as Row;
          return {
            ...(r as Partial<Transaction>),
            transaction_date: (asString(r.transaction_date) ?? asString(r.date) ?? undefined) as string,
          };
        });
    }
  }
  return [];
}

function pickGroups(result: Row | null): { label: string; total: number; count: number | null }[] {
  const groups = result?.groups;
  if (!Array.isArray(groups)) return [];
  return groups
    .map((g) => asRecord(g))
    .filter((g): g is Row => g !== null)
    .map((g) => ({
      label:
        asString(g.category) ?? asString(g.merchant) ?? asString(g.month) ?? asString(g.label) ?? "Other",
      total: Math.abs(asNumber(g.total) ?? 0),
      count: asNumber(g.count),
    }))
    .sort((a, b) => b.total - a.total);
}

/** Plain-English description of what was looked up. */
function describeFilters(params: Row, result: Row | null): { icon: "date" | "filter"; text: string }[] {
  const filters = asRecord(result?.filters) ?? {};
  const out: { icon: "date" | "filter"; text: string }[] = [];

  const period = asString(filters.period) ?? asString(params.period);
  const start = asString(filters.start_date) ?? asString(params.start_date);
  const end = asString(filters.end_date) ?? asString(params.end_date);
  const range = start && end ? `${formatDate(start)} – ${formatDate(end)}` : null;
  if (period || range) {
    const label = period ? PERIOD_LABELS[period] ?? period : null;
    out.push({ icon: "date", text: [label, range && `(${range})`].filter(Boolean).join(" ") });
  }

  const category = asString(filters.category) ?? asString(params.category);
  if (category) out.push({ icon: "filter", text: `Category: ${category}` });

  const merchant = asString(params.merchant);
  if (merchant) out.push({ icon: "filter", text: `Merchant: ${merchant}` });

  const txType = asString(filters.transaction_type) ?? asString(params.transaction_type);
  if (txType && TYPE_LABELS[txType]) out.push({ icon: "filter", text: TYPE_LABELS[txType] });

  const groupBy = asString(params.group_by);
  if (groupBy && GROUP_LABELS[groupBy]) out.push({ icon: "filter", text: GROUP_LABELS[groupBy] });

  const query = asString(params.query);
  if (query) out.push({ icon: "filter", text: `Search: “${query}”` });

  const expression = asString(params.expression);
  if (expression) out.push({ icon: "filter", text: `Math: ${expression}` });

  return out;
}

function sourceLabel(tool: string | undefined): string {
  if (!tool) return "Source data";
  return SOURCE_LABELS[tool] ?? "Source data";
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
  const params = (evidence?.params ?? {}) as Row;
  const filters = describeFilters(params, result);
  const groups = pickGroups(result);
  const txs = pickTransactions(result);
  const maxGroup = groups[0]?.total ?? 0;
  const groupTotal = groups.reduce((sum, g) => sum + g.total, 0);

  const singleTotal = result?.group_by === "none" ? asNumber(result.total) : null;
  const singleCount = result?.group_by === "none" ? asNumber(result.count) : null;
  const calcValue = evidence?.tool === "calculate" ? asNumber(result?.result ?? result?.value) : null;
  const broadened = result?.broadened === true;
  const errorText = asString(result?.error);

  const hasFriendlyView =
    filters.length > 0 || groups.length > 0 || txs.length > 0 || singleTotal !== null || calcValue !== null;

  return (
    <>
      <button
        type="button"
        className="evidence-drawer-backdrop"
        aria-label="Close"
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
            <p className="eyebrow">Where this number comes from</p>
            <h2
              id="evidence-drawer-title"
              className="mt-1 text-base font-semibold text-[var(--foreground)]"
            >
              {sourceLabel(evidence?.tool)}
            </h2>
          </div>
          <button type="button" onClick={onClose} className="icon-btn" aria-label="Close">
            <X size={16} />
          </button>
        </div>

        <div className="flex flex-1 flex-col gap-5 overflow-y-auto px-5 py-4">
          {!evidence ? (
            <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] px-4 py-6 text-center">
              <Database size={22} className="mx-auto text-[var(--muted)]" />
              <p className="mt-3 text-sm text-[var(--muted)]">
                The source for this number isn&apos;t available for this reply.
              </p>
            </div>
          ) : (
            <>
              {filters.length > 0 && (
                <section>
                  <h3 className="section-title mb-2">What we looked at</h3>
                  <ul className="flex flex-wrap gap-2">
                    {filters.map((f) => (
                      <li
                        key={f.text}
                        className="inline-flex items-center gap-1.5 rounded-lg border border-[var(--border)] bg-[var(--surface)] px-2.5 py-1 text-xs text-[var(--foreground)]"
                      >
                        {f.icon === "date" ? (
                          <Calendar size={12} className="text-[var(--accent)]" />
                        ) : (
                          <Filter size={12} className="text-[var(--accent)]" />
                        )}
                        {f.text}
                      </li>
                    ))}
                  </ul>
                  {broadened && (
                    <p className="mt-2 text-xs text-[var(--muted)]">
                      Nothing matched the period you asked about, so this shows the most recent month
                      that has data.
                    </p>
                  )}
                </section>
              )}

              {errorText && (
                <p className="rounded-xl border border-[var(--border)] bg-[var(--surface)] px-4 py-3 text-sm text-[var(--muted)]">
                  This lookup didn&apos;t return data: {errorText}
                </p>
              )}

              {singleTotal !== null && (
                <section className="rounded-xl border border-[var(--border)] bg-[var(--surface)] px-4 py-4">
                  <p className="text-xs text-[var(--muted)]">Total</p>
                  <p className="mt-1 text-2xl font-semibold tabular-nums text-[var(--foreground)]">
                    {formatCurrency(singleTotal)}
                  </p>
                  {singleCount !== null && (
                    <p className="mt-1 text-xs text-[var(--muted)]">
                      Across {singleCount} transaction{singleCount === 1 ? "" : "s"}
                    </p>
                  )}
                </section>
              )}

              {calcValue !== null && (
                <section className="rounded-xl border border-[var(--border)] bg-[var(--surface)] px-4 py-4">
                  <p className="text-xs text-[var(--muted)]">Result</p>
                  <p className="mt-1 text-2xl font-semibold tabular-nums text-[var(--foreground)]">
                    {calcValue.toLocaleString("en-CA", { maximumFractionDigits: 2 })}
                  </p>
                </section>
              )}

              {groups.length > 0 && (
                <section>
                  <div className="mb-2 flex items-baseline justify-between">
                    <h3 className="section-title">Breakdown</h3>
                    <span className="text-xs tabular-nums text-[var(--muted)]">
                      Total {formatCurrency(groupTotal)}
                    </span>
                  </div>
                  <ul className="flex flex-col gap-2.5">
                    {groups.slice(0, 15).map((g) => (
                      <li key={g.label}>
                        <div className="flex items-baseline justify-between gap-3 text-sm">
                          <span className="truncate text-[var(--foreground)]">{g.label}</span>
                          <span className="shrink-0 tabular-nums font-medium text-[var(--foreground)]">
                            {formatCurrency(g.total)}
                          </span>
                        </div>
                        <div className="mt-1 flex items-center gap-2">
                          <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-[var(--border)]">
                            <div
                              className="h-full rounded-full bg-[var(--accent)]"
                              style={{ width: `${maxGroup ? Math.max(3, (g.total / maxGroup) * 100) : 0}%` }}
                            />
                          </div>
                          {g.count !== null && (
                            <span className="w-14 shrink-0 text-right text-[11px] text-[var(--muted)]">
                              {g.count} txn{g.count === 1 ? "" : "s"}
                            </span>
                          )}
                        </div>
                      </li>
                    ))}
                  </ul>
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
                            {tx.merchant ?? tx.description ?? "Transaction"}
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
                    <p className="mt-2 text-xs text-[var(--muted)]">Showing 25 of {txs.length}</p>
                  )}
                </section>
              )}

              {!hasFriendlyView && !errorText && asString(result?.summary) && (
                <p className="rounded-xl border border-[var(--border)] bg-[var(--surface)] px-4 py-3 text-sm text-[var(--foreground)]">
                  {asString(result?.summary)}
                </p>
              )}

              <details className="group mt-auto rounded-xl border border-[var(--border)] bg-[var(--surface)]">
                <summary className="flex cursor-pointer list-none items-center gap-1.5 px-3 py-2 text-xs font-medium text-[var(--muted)]">
                  <ChevronRight size={12} className="transition-transform group-open:rotate-90" />
                  Technical details
                </summary>
                <div className="border-t border-[var(--border)] px-3 py-2 text-[11px] text-[var(--muted)]">
                  Reference {evidenceId} · {evidence.tool}
                </div>
                <pre className="evidence-code rounded-none border-0 border-t border-[var(--border)]">
                  {JSON.stringify({ params, result }, null, 2)}
                </pre>
              </details>
            </>
          )}
        </div>
      </aside>
    </>
  );
}
