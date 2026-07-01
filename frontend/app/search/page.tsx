"use client";

import {
  ArrowDownLeft,
  ArrowUpRight,
  Car,
  Clock,
  Coffee,
  Download,
  Film,
  Home,
  Loader2,
  Receipt,
  Search,
  ShoppingBag,
  Sparkles,
  Trash2,
  TrendingUp,
  Utensils,
} from "lucide-react";
import { useEffect, useRef, useState, type CSSProperties } from "react";

import { PageHeader } from "@/components/ui/PageHeader";
import { useToast } from "@/contexts/ToastContext";
import { api } from "@/lib/api";
import type { Transaction } from "@/lib/types";
import { getCategoryColor } from "@/lib/types";
import { exportToCsv, formatCurrency, formatDate } from "@/lib/utils";

const SEARCH_PRESETS = [
  {
    id: "dining",
    label: "Dining & coffee",
    query: "Coffee shops, restaurants, and takeout spending",
    icon: Coffee,
    accent: "#f59e0b",
  },
  {
    id: "groceries",
    label: "Groceries",
    query: "Grocery store and supermarket purchases",
    icon: ShoppingBag,
    accent: "#22c55e",
  },
  {
    id: "subscriptions",
    label: "Subscriptions",
    query: "Recurring subscription and streaming charges",
    icon: Receipt,
    accent: "#6366f1",
  },
  {
    id: "transport",
    label: "Transport",
    query: "Uber, transit, gas, and commute expenses",
    icon: Car,
    accent: "#3b82f6",
  },
  {
    id: "housing",
    label: "Housing & rent",
    query: "Rent, mortgage, and housing related payments",
    icon: Home,
    accent: "#8b5cf6",
  },
  {
    id: "entertainment",
    label: "Entertainment",
    query: "Movies, events, and entertainment spending",
    icon: Film,
    accent: "#f97316",
  },
  {
    id: "large",
    label: "Large purchases",
    query: "Transactions over one hundred dollars",
    icon: TrendingUp,
    accent: "#ec4899",
  },
  {
    id: "income",
    label: "Income & deposits",
    query: "Payroll deposits and incoming transfers",
    icon: ArrowUpRight,
    accent: "#10b981",
  },
] as const;

const TIME_FILTERS = [
  { id: "any", label: "Any time", suffix: "" },
  { id: "month", label: "This month", suffix: " this month" },
  { id: "last", label: "Last month", suffix: " last month" },
  { id: "quarter", label: "Last 3 months", suffix: " in the last 3 months" },
] as const;

const HISTORY_KEY = "finsight_search_history";

function loadHistory(): string[] {
  try {
    return JSON.parse(localStorage.getItem(HISTORY_KEY) ?? "[]") as string[];
  } catch {
    return [];
  }
}

function saveHistory(history: string[]) {
  localStorage.setItem(HISTORY_KEY, JSON.stringify(history.slice(0, 10)));
}

export default function SearchPage() {
  const { toast } = useToast();
  const [query, setQuery] = useState("");
  const [timeFilter, setTimeFilter] = useState<(typeof TIME_FILTERS)[number]["id"]>("any");
  const [results, setResults] = useState<Transaction[]>([]);
  const [embeddingEnabled, setEmbeddingEnabled] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<string[]>(() => {
    if (typeof window === "undefined") return [];
    return loadHistory();
  });
  const [activePreset, setActivePreset] = useState<string | null>(null);
  const [needsReindex, setNeedsReindex] = useState(false);
  const [reindexing, setReindexing] = useState(false);
  const [reindexProgress, setReindexProgress] = useState<string | null>(null);
  const [indexedCount, setIndexedCount] = useState<number | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    void api.searchStatus().then((status) => {
      setNeedsReindex(status.needs_reindex);
      setIndexedCount(status.indexed_count);
      if (!status.embedding_enabled) {
        setEmbeddingEnabled(false);
      }
    }).catch(() => {
      // non-blocking
    });
  }, []);

  const handleReindex = async () => {
    setReindexing(true);
    setError(null);
    setReindexProgress(null);
    try {
      let totalThisRun = 0;
      let last: Awaited<ReturnType<typeof api.reindexSearch>> | null = null;
      for (let i = 0; i < 200; i += 1) {
        const res = await api.reindexSearch();
        last = res;
        totalThisRun += res.indexed;
        setIndexedCount(res.indexed_count);
        if (res.transaction_count > 0) {
          setReindexProgress(`${res.indexed_count} / ${res.transaction_count}`);
        }
        if (res.complete || res.indexed === 0) break;
        // Voyage free tier without billing card: ~3 requests/minute
        await new Promise((resolve) => setTimeout(resolve, 22_000));
      }
      if (last?.complete) {
        setNeedsReindex(false);
        toast(
          `Indexed ${last.indexed_count} transaction${last.indexed_count === 1 ? "" : "s"} for search`,
          "success",
        );
      } else if (totalThisRun > 0) {
        toast(`Indexed ${totalThisRun} so far — tap rebuild again to continue`, "info");
      } else {
        setError("Nothing was indexed. Check Voyage API key on Render and try again.");
      }
    } catch (e) {
      const raw = e instanceof Error ? e.message : "Reindex failed";
      setError(raw.replace(/^API \d+:\s*/i, ""));
    } finally {
      setReindexing(false);
      setReindexProgress(null);
    }
  };

  const buildQuery = (base: string) => {
    const tf = TIME_FILTERS.find((t) => t.id === timeFilter);
    return `${base}${tf?.suffix ?? ""}`.trim();
  };

  const handleSearch = async (q?: string, presetId?: string) => {
    const raw = (q ?? query).trim();
    if (!raw) return;
    const sq = buildQuery(raw);
    setLoading(true);
    setError(null);
    setSearched(true);
    if (q) setQuery(raw);
    if (presetId) setActivePreset(presetId);
    else setActivePreset(null);
    try {
      const res = await api.search(sq, 10);
      setResults(res.results);
      setEmbeddingEnabled(res.embedding_enabled);
      const next = [raw, ...history.filter((h) => h !== raw)];
      setHistory(next);
      saveHistory(next);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Search failed");
    } finally {
      setLoading(false);
    }
  };

  const clearHistory = () => {
    setHistory([]);
    localStorage.removeItem(HISTORY_KEY);
    toast("Search history cleared", "info");
  };

  const handleExport = () => {
    exportToCsv(`search-results-${new Date().toISOString().slice(0, 10)}.csv`, [
      ["Rank", "Date", "Description", "Amount", "Category", "Merchant"],
      ...results.map((t, i) => [
        String(i + 1),
        t.transaction_date,
        t.description,
        String(t.amount),
        t.category,
        t.merchant ?? "",
      ]),
    ]);
    toast(`Exported ${results.length} results`);
  };

  return (
    <div className="page-container max-w-4xl gap-8">
      <PageHeader
        eyebrow="Find transactions"
        title="Smart"
        titleAccent="Search"
        subtitle="Describe what you're looking for in plain English — FinSight finds the most relevant transactions."
      />

      {/* Hero search */}
      <section className="panel panel-glow rounded-2xl p-6 md:p-8">
        <div className="chat-search-wrap">
          <Search size={18} className="chat-search-icon" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") void handleSearch();
            }}
            placeholder="e.g. What did I spend on Uber last month?"
            className="input-field chat-search-input py-3.5 text-base"
          />
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-2">
          <span className="text-xs font-medium text-[var(--muted)]">Time:</span>
          {TIME_FILTERS.map((tf) => (
            <button
              key={tf.id}
              type="button"
              onClick={() => setTimeFilter(tf.id)}
              className={[
                "rounded-full border px-3 py-1 text-xs font-medium transition-colors",
                timeFilter === tf.id
                  ? "border-[var(--accent)]/40 bg-[var(--accent-soft)] text-[var(--accent)]"
                  : "border-[var(--border)] text-[var(--muted)] hover:border-[var(--border-glow)] hover:text-[var(--foreground)]",
              ].join(" ")}
            >
              {tf.label}
            </button>
          ))}
        </div>

        <button
          type="button"
          onClick={() => void handleSearch()}
          disabled={!query.trim() || loading}
          className="btn-primary mt-5 flex w-full items-center justify-center gap-2 rounded-xl py-3 text-sm font-medium disabled:opacity-40 sm:w-auto sm:px-8"
        >
          {loading ? (
            <>
              <Loader2 size={16} className="animate-spin" />
              Searching…
            </>
          ) : (
            <>
              <Sparkles size={16} />
              Search transactions
            </>
          )}
        </button>
      </section>

      {/* Preset categories */}
      {!searched && (
        <>
          <section>
            <h2 className="section-title mb-1">Search by topic</h2>
            <p className="mb-4 text-sm text-[var(--muted)]">
              Tap a category to run a curated search instantly.
            </p>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {SEARCH_PRESETS.map((preset, i) => {
                const Icon = preset.icon;
                return (
                  <button
                    key={preset.id}
                    type="button"
                    onClick={() => void handleSearch(preset.query, preset.id)}
                    className="search-preset-card panel-interactive stagger-item text-left"
                    style={{ "--stagger": i + 1 } as CSSProperties}
                  >
                    <span
                      className="search-preset-icon"
                      style={{ backgroundColor: `${preset.accent}20`, color: preset.accent }}
                    >
                      <Icon size={18} />
                    </span>
                    <p className="text-sm font-medium text-[var(--foreground)]">{preset.label}</p>
                    <p className="mt-1 text-xs leading-relaxed text-[var(--muted)] line-clamp-2">
                      {preset.query}
                    </p>
                  </button>
                );
              })}
            </div>
          </section>

          {history.length > 0 && (
            <section className="panel rounded-2xl p-5">
              <div className="mb-3 flex items-center justify-between">
                <h2 className="section-title">Recent searches</h2>
                <button
                  type="button"
                  onClick={clearHistory}
                  className="flex items-center gap-1 text-xs text-[var(--muted)] hover:text-[var(--foreground)]"
                >
                  <Trash2 size={12} />
                  Clear
                </button>
              </div>
              <ul className="flex flex-col gap-1">
                {history.map((h) => (
                  <li key={h}>
                    <button
                      type="button"
                      onClick={() => void handleSearch(h)}
                      className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm text-[var(--muted)] transition-colors hover:bg-[var(--surface)] hover:text-[var(--foreground)]"
                    >
                      <Clock size={14} className="shrink-0 opacity-60" />
                      <span className="truncate">{h}</span>
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </>
      )}

      {needsReindex && (
        <div className="flex flex-col gap-3 rounded-xl border border-amber-500/30 bg-amber-500/5 p-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-3">
            <Sparkles size={16} className="mt-0.5 shrink-0 text-amber-500" />
            <div>
              <p className="text-sm font-medium text-[var(--foreground)]">
                Search index needs a rebuild
              </p>
              <p className="mt-1 text-xs text-[var(--muted)]">
                Your transactions are saved, but semantic search was reset during the Voyage upgrade.
                Rebuild once to make Smart Search work again.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => void handleReindex()}
            disabled={reindexing}
            className="btn-primary shrink-0 rounded-xl px-4 py-2 text-sm"
          >
            {reindexing
              ? reindexProgress
                ? `Indexing ${reindexProgress} (Voyage limits — ~20s/batch)…`
                : "Indexing…"
              : "Rebuild search index"}
          </button>
        </div>
      )}

      {embeddingEnabled === false && !needsReindex && (
        <div className="flex items-start gap-3 rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4">
          <Sparkles size={16} className="mt-0.5 shrink-0 text-[var(--accent)]" />
          <div>
            <p className="text-sm font-medium text-[var(--foreground)]">Smart search is setting up</p>
            <p className="mt-1 text-xs text-[var(--muted)]">
              Upload transactions first — semantic search activates once your data is indexed.
            </p>
          </div>
        </div>
      )}

      {error && (
        <div className="rounded-xl border border-rose-500/25 bg-rose-500/5 px-4 py-3 text-sm text-rose-400">
          {error}
        </div>
      )}

      {searched && !loading && (
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="section-title">
              {results.length > 0
                ? `${results.length} result${results.length !== 1 ? "s" : ""}`
                : "No results"}
            </h2>
            <p className="mt-0.5 text-xs text-[var(--muted)]">
              {activePreset
                ? `Showing matches for ${SEARCH_PRESETS.find((p) => p.id === activePreset)?.label}`
                : `Best matches for “${query}”`}
            </p>
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => {
                setSearched(false);
                setResults([]);
                setActivePreset(null);
              }}
              className="btn-ghost rounded-xl px-3 py-2 text-xs"
            >
              New search
            </button>
            {results.length > 0 && (
              <button
                type="button"
                onClick={handleExport}
                className="btn-ghost flex items-center gap-1.5 rounded-xl px-3 py-2 text-xs"
              >
                <Download size={13} />
                Export
              </button>
            )}
          </div>
        </div>
      )}

      {searched && !loading && results.length === 0 && embeddingEnabled && !needsReindex && (
        <div className="panel flex flex-col items-center gap-3 rounded-2xl py-14 text-center">
          <Utensils size={28} className="text-[var(--muted)]" />
          <p className="text-sm text-[var(--muted)]">
            {indexedCount === 0
              ? "No indexed transactions yet. Rebuild the search index above, or upload a CSV."
              : "No matching transactions. Try a preset above or broaden your time range."}
          </p>
        </div>
      )}

      {loading && (
        <div className="panel flex flex-col divide-y divide-[var(--border)] rounded-2xl">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="flex items-center gap-4 px-5 py-4">
              <div className="h-10 w-10 shimmer rounded-xl" />
              <div className="flex flex-1 flex-col gap-2">
                <div className="h-3.5 w-3/4 shimmer rounded" />
                <div className="h-3 w-1/2 shimmer rounded" />
              </div>
              <div className="h-4 w-16 shimmer rounded" />
            </div>
          ))}
        </div>
      )}

      {results.length > 0 && !loading && (
        <div className="panel flex flex-col divide-y divide-[var(--border)] rounded-2xl overflow-hidden">
          {results.map((tx, idx) => (
            <div
              key={tx.id}
              className="flex items-center gap-4 px-5 py-4 transition-colors hover:bg-[var(--accent-soft)]/20"
            >
              <span className="w-6 shrink-0 text-center text-xs font-semibold tabular-nums text-[var(--muted)]">
                {idx + 1}
              </span>
              <div
                className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl"
                style={{ backgroundColor: `${getCategoryColor(tx.category)}20` }}
              >
                {tx.amount < 0 ? (
                  <ArrowDownLeft size={16} style={{ color: getCategoryColor(tx.category) }} />
                ) : (
                  <ArrowUpRight size={16} className="text-emerald-400" />
                )}
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-[var(--foreground)]">
                  {tx.description}
                </p>
                <p className="mt-0.5 flex flex-wrap items-center gap-x-1.5 text-xs text-[var(--muted)]">
                  <span
                    className="rounded-full px-2 py-0.5 text-[10px] font-medium"
                    style={{
                      backgroundColor: `${getCategoryColor(tx.category)}20`,
                      color: getCategoryColor(tx.category),
                    }}
                  >
                    {tx.category}
                  </span>
                  {tx.merchant && <span>· {tx.merchant}</span>}
                  <span>· {formatDate(tx.transaction_date)}</span>
                </p>
              </div>
              <span
                className={[
                  "shrink-0 text-sm font-semibold tabular-nums",
                  tx.amount < 0 ? "text-rose-400" : "text-emerald-400",
                ].join(" ")}
              >
                {tx.amount < 0 ? "−" : "+"}
                {formatCurrency(tx.amount)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
