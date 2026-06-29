"use client";

import {
  ArrowDownLeft,
  ArrowUpRight,
  Clock,
  Download,
  Search,
  Sparkles,
  Trash2,
  Zap,
} from "lucide-react";
import { useRef, useState } from "react";

import { useToast } from "@/contexts/ToastContext";
import { api } from "@/lib/api";
import type { Transaction } from "@/lib/types";
import { getCategoryColor } from "@/lib/types";
import { exportToCsv, formatCurrency, formatDate } from "@/lib/utils";

const EXAMPLE_QUERIES = [
  "Coffee and dining last month",
  "Subscription services",
  "Grocery spending",
  "Large purchases over $100",
  "Transport and commute",
  "Entertainment spending",
];

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
  const [results, setResults] = useState<Transaction[]>([]);
  const [embeddingEnabled, setEmbeddingEnabled] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<string[]>(() => {
    if (typeof window === "undefined") return [];
    return loadHistory();
  });
  const [kValue, setKValue] = useState(8);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSearch = async (q?: string) => {
    const sq = (q ?? query).trim();
    if (!sq) return;
    setLoading(true);
    setError(null);
    setSearched(true);
    if (q) setQuery(q);
    try {
      const res = await api.search(sq, kValue);
      setResults(res.results);
      setEmbeddingEnabled(res.embedding_enabled);
      // Update history
      const next = [sq, ...history.filter((h) => h !== sq)];
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
        String(i + 1), t.transaction_date, t.description,
        String(t.amount), t.category, t.merchant ?? "",
      ]),
    ]);
    toast(`Exported ${results.length} results`);
  };

  return (
    <div className="page-container">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2">
          <h1 className="text-xl font-semibold text-zinc-50">AI Search</h1>
          <span className="flex items-center gap-1 rounded-full bg-indigo-500/10 px-2.5 py-0.5 text-xs text-indigo-400">
            <Sparkles size={10} /> Voyage AI voyage-3
          </span>
        </div>
        <p className="mt-1 text-sm text-zinc-500">
          Ask a natural-language question to semantically retrieve your most relevant transactions.
        </p>
      </div>

      {/* Search input + k-selector */}
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-zinc-500" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") void handleSearch(); }}
            placeholder="e.g. What did I spend on food last month?"
            className="w-full rounded-xl border border-zinc-700 bg-zinc-900 py-3 pl-10 pr-4 text-sm text-zinc-200 placeholder-zinc-600 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          />
        </div>
        <select value={kValue} onChange={(e) => setKValue(Number(e.target.value))}
          className="rounded-xl border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-400 focus:outline-none focus:ring-1 focus:ring-indigo-500">
          {[3, 5, 8, 10, 15, 20].map((n) => <option key={n} value={n}>Top {n}</option>)}
        </select>
        <button onClick={() => void handleSearch()} disabled={!query.trim() || loading}
          className="flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-3 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-40">
          <Zap size={14} />
          {loading ? "Searching…" : "Search"}
        </button>
      </div>

      {/* History + examples */}
      {!searched && (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {/* Examples */}
          <div className="flex flex-col gap-3">
            <p className="text-xs font-medium text-zinc-600">Try an example</p>
            <div className="flex flex-wrap gap-2">
              {EXAMPLE_QUERIES.map((q) => (
                <button key={q} onClick={() => void handleSearch(q)}
                  className="rounded-full border border-zinc-800 bg-zinc-900 px-3 py-1.5 text-xs text-zinc-400 hover:border-indigo-600 hover:text-indigo-300">
                  {q}
                </button>
              ))}
            </div>
          </div>

          {/* History */}
          {history.length > 0 && (
            <div className="flex flex-col gap-3">
              <div className="flex items-center justify-between">
                <p className="text-xs font-medium text-zinc-600">Recent searches</p>
                <button onClick={clearHistory} className="flex items-center gap-1 text-xs text-zinc-700 hover:text-zinc-500">
                  <Trash2 size={11} /> Clear
                </button>
              </div>
              <ul className="flex flex-col gap-1">
                {history.map((h) => (
                  <li key={h}>
                    <button onClick={() => void handleSearch(h)}
                      className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-zinc-400 hover:bg-zinc-900 hover:text-zinc-200">
                      <Clock size={13} className="text-zinc-600" />
                      {h}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Embedding not configured */}
      {embeddingEnabled === false && (
        <div className="flex items-start gap-3 rounded-xl border border-amber-800/50 bg-amber-900/20 p-4">
          <Sparkles size={16} className="mt-0.5 shrink-0 text-amber-400" />
          <div>
            <p className="text-sm font-medium text-amber-300">Embeddings not configured</p>
            <p className="mt-1 text-xs text-amber-500">
              Set <code className="text-amber-400">VOYAGE_API_KEY</code> in your{" "}
              <code className="text-amber-400">.env</code> file and re-ingest transactions to enable semantic search.
              Get a free key at{" "}
              <a href="https://www.voyageai.com" target="_blank" rel="noreferrer" className="underline hover:text-amber-300">
                voyageai.com
              </a>.
            </p>
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-red-800/50 bg-red-900/20 px-4 py-3 text-sm text-red-400">{error}</div>
      )}

      {/* Results header */}
      {results.length > 0 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-zinc-400">
            <span className="font-medium text-zinc-200">{results.length}</span> result{results.length !== 1 ? "s" : ""}
            {" "}·{" "}
            <span className="text-zinc-600">ranked by semantic similarity to</span>{" "}
            <span className="italic text-zinc-500">&ldquo;{query}&rdquo;</span>
          </p>
          <button onClick={handleExport}
            className="flex items-center gap-1.5 rounded-lg border border-zinc-700 px-3 py-1.5 text-xs text-zinc-400 hover:text-zinc-100">
            <Download size={12} /> Export
          </button>
        </div>
      )}

      {/* No results */}
      {searched && !loading && results.length === 0 && embeddingEnabled && (
        <div className="py-12 text-center text-sm text-zinc-600">
          No matching transactions found. Try a different query or upload transactions first.
        </div>
      )}

      {/* Results list */}
      {results.length > 0 && (
        <div className="flex flex-col divide-y divide-zinc-800/60 panel rounded-2xl">
          {results.map((tx, idx) => (
            <div key={tx.id} className="flex items-center gap-4 px-5 py-3.5 transition-colors hover:bg-zinc-800/40">
              <span className="w-5 shrink-0 text-center text-xs font-semibold text-zinc-700">{idx + 1}</span>
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg"
                style={{ backgroundColor: getCategoryColor(tx.category) + "20" }}>
                {tx.amount < 0
                  ? <ArrowDownLeft size={14} style={{ color: getCategoryColor(tx.category) }} />
                  : <ArrowUpRight size={14} className="text-emerald-400" />
                }
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-zinc-200">{tx.description}</p>
                <p className="text-xs text-zinc-500">
                  <span className="rounded-full px-1.5 py-0.5 text-[10px] font-medium"
                    style={{ backgroundColor: getCategoryColor(tx.category) + "20", color: getCategoryColor(tx.category) }}>
                    {tx.category}
                  </span>
                  {tx.merchant ? <> · {tx.merchant}</> : null}
                  {" · "}
                  {formatDate(tx.transaction_date)}
                </p>
              </div>
              <span className={["shrink-0 text-sm font-semibold tabular-nums",
                tx.amount < 0 ? "text-rose-400" : "text-emerald-400",
              ].join(" ")}>
                {tx.amount < 0 ? "−" : "+"}{formatCurrency(tx.amount)}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Loading skeleton */}
      {loading && (
        <div className="flex flex-col gap-1 panel rounded-2xl p-2">
          {Array.from({ length: kValue }).map((_, i) => (
            <div key={i} className="flex items-center gap-4 p-3">
              <div className="h-9 w-9 shimmer rounded-lg" />
              <div className="flex flex-1 flex-col gap-2">
                <div className="h-3.5 w-3/4 shimmer rounded" />
                <div className="h-3 w-1/2 shimmer rounded" />
              </div>
              <div className="h-4 w-16 shimmer rounded" />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
